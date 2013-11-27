from __future__ import absolute_import
import boto.ec2
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import freezr.util as util

TERMINAL_STATES = ('shutting-down', 'terminated')
DRY_RUN = False # really only for debugging

class AwsInterface(util.Logger):
    """This is the interface to AWS.

    The AWS interface can have knowledge of the data model, e.g. it is
    allowed to modify and update accounts, projects, instances
    etc. This is a separate class to make testing easier, and also to
    move a lot of aws-specific code out of the model classes
    themselves (lest they bloat)."""

    def __init__(self, account):
        super(AwsInterface, self).__init__()
        self.account = account
        self.conns = {}

    def disconnect(self):
        self.conns = {}

    def connect_ec2(self, region):
        if region in self.conns:
            return self.conns[region]

        self.conns[region] = boto.ec2.connect_to_region(
            region,
            aws_access_key_id=self.account.access_key,
            aws_secret_access_key=self.account.secret_key)

        self.log.debug("Connected to region %s on account %s: %r",
                       region, self.account, self.conns[region])

        return self.conns[region]

    def refresh_instance(self, instance):
        """Refreshes information on the given instance."""
        conn = self.connect_ec2(instance.region)

        for instance_data in conn.get_only_instances(instance_ids=[instance.instance_id]):
            assert instance_data.id == instance.instance_id
            if instance_data.state not in TERMINAL_STATES:
                self.update_instance_record(instance, instance_data)
                instance.save()
                return

        # Fall through here if instance doesn't exist, or it is or is
        # going to be terminated.

        self.log.debug('Instance %s gone away, removing', instance)
        instance.delete()

    def update_instance_record(self, record, instance):
        record.state = instance.state
        record.vpc_id = instance.vpc_id
        record.store = instance.root_device_type
        record.type = instance.instance_type

    def refresh_region(self, account, region):
        """Refreshes given `account` information on `region`. Returns
        a three-value tuple (total, added, deleted) where `total` is
        the number of instances seen during this update, `added` those
        that were new (added new instance records to database) and
        `deleted` those that had gone away, and were deleted from
        database."""

        conn = self.connect_ec2(region)

        if not conn:
            account.log_entry('Could not connect to region %s', type='error')
            return

        ## Basically just iterate through all instances in this
        ## account, compare that set to existing data records, update
        ## those that match, remove those that don't match.

        # Set of alive instance ids we've seen
        seen_instances = set()

        # Set of instances added
        added_instances = set()

        for instance in conn.get_only_instances():
            self.log.debug("Got instance id %s: region=%s state=%s vpc_id=%s store=%s",
                           instance.id, region,
                           instance.state, instance.vpc_id,
                           instance.root_device_type)

            # These will be skipped in our counts completely. These
            # will also get removed since they are not put into seen_instances
            # set.
            if instance.state in TERMINAL_STATES:
                continue

            try:
                record = account.instances.get(instance_id=instance.id,
                                                region=region)
            except ObjectDoesNotExist:
                record = account.new_instance(instance_id=instance.id,
                                              region=region)
                added_instances.add(record)
            except MultipleObjectsReturned:
                # Ahem, this shouldn't be happening. We have bad
                # records, make them go away.
                account.instances.filter(instance_id=instance.id,
                                          region=region).delete()
                continue

            # Although none of these should change during lifetime of
            # an instance, let's still be careful -- freezr might have
            # been dead for 50 hours and new instances with the same
            # id could have gotten around (in the same account and
            # region).
            self.update_instance_record(record, instance)

            seen_instances.add(record)
            record.save()

            tags = set(record.tags.all())
            seen_tags = set()

            for key, value in instance.tags.iteritems():
                try:
                    tag = record.tags.get(key=key)
                except ObjectDoesNotExist:
                    tag = record.new_tag(key=key)

                if tag.value != value:
                    tag.value = value

                seen_tags.add(tag)
                tag.save()

            # See which tags have been removed
            for missing_tag in (tags - seen_tags):
                missing_tag.delete()

            self.log.debug("Instance %s tags: %r", instance.id, seen_tags)

            # TODO: zone, ami, sgs (sg[foo] for test?), product codes,
            # monitoring state, subnet id, arch, virt, hypervisor,
            # network interfaces, sourcecheck, ebsoptimized, eips,
            # tenancy

        # Now go through previously recorded instances for this
        # account and see whether they are actually present in seen_instances
        # ones.
        recorded_instances = set(account.instances.filter(region=region).all())
        disappeared_instances = recorded_instances - seen_instances
        self.log.debug("alive=%r recorded=%r added=%r disappeared=%r",
                       seen_instances, recorded_instances,
                       added_instances, disappeared_instances)

        for record in disappeared_instances:
            record.delete()

        self.log.info("Updated account %s in region %s: #alive=%d #recorded=%d #added=%d #disappeared=%d",
                      self, region,
                      len(seen_instances), len(recorded_instances),
                      len(added_instances), len(disappeared_instances))

        return (len(seen_instances),
                len(added_instances),
                len(disappeared_instances))

    def terminate_instance(self, instance):
        """Terminates the given instance, updating its status as
        needed.

        This *does not* do the double-termination trick to get rid of
        the instance metadata. We'll leave it lingering so humans can
        also see that result from AWS console, if needed."""

        if DRY_RUN:
            return

        conn = self.connect_ec2(instance.region)
        result = conn.terminate_instances(instance_ids=[instance.instance_id])

        self.log.debug("terminate_instance: %s => %s", instance, result)

    def freeze_instance(self, instance):
        """Freeze the given instance."""
        self.log.debug("freeze_instance: %s, state %s",
                       instance, instance.state)

        if DRY_RUN:
            return

        if instance.state != 'running':
            # TODO: add suitable exception
            return

        conn = self.connect_ec2(instance.region)
        result = conn.stop_instances(instance_ids=[instance.instance_id])

        self.log.debug("freeze_instance: %s => %s", instance, result)


    def thaw_instance(self, instance):
        """Thaw the given instance."""
        self.log.debug("thaw_instance: %s, state %s",
                       instance, instance.state)
        if DRY_RUN:
            return

        if instance.state != 'stopped':
            return

        conn = self.connect_ec2(instance.region)
        result = conn.start_instances(instance_ids=[instance.instance_id])

        self.log.debug("thaw_instance: %s => %s", instance, result)

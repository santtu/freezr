from __future__ import absolute_import
import boto.ec2
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import freezr.util as util

# This file contains mix-ins for model.* classes. We do this here
# separately to avoid putting a lot of AWS-specific code into the
# model.py file. It also allows us to keep a better separation of
# concerns.

class BaseAWS(util.Logger):
    """Common base class for common tasks, like getting EC2 connection
    from an account.

    This class, and its descendants assume that you have
    freezr.util.Logger mixed in to the instance."""
    def connect_ec2(self, region):
        conn = boto.ec2.connect_to_region(
            region,
            aws_access_key_id=self.account.access_key,
            aws_secret_access_key=self.account.secret_key)

        self.log.debug("Connected to region %s on account %s: %r",
                       region, self.account, conn)

        return conn

    def __init__(self, account=None):
        super(BaseAWS, self).__init__()
        self.account = account

class Account(BaseAWS):
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
            if instance.state in ('shutting-down', 'terminated'):
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
            record.state = instance.state
            record.vpc_id = instance.vpc_id
            record.store = instance.root_device_type
            record.type = instance.instance_type

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

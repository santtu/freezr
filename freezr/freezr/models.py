from __future__ import absolute_import
from django.db import models
from django.core.validators import validate_slug
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.contrib import auth
from django.utils import timezone
import re
import freezr.util as util
import freezr.aws as aws
import freezr.filter as filter

VALID_INSTANCE_RE = re.compile(r'^i-[0-9a-f]+$')

def validate_instance_id(value):
    if not VALID_INSTANCE_RE.match(value):
        raise ValidationError(u'%s is not a valid instance id' % value)

def firsts(elts):
    return map(lambda e: e[0], elts)

# Should get this dynamically from AWS instead
EC2_REGIONS_CHOICES = (
    ('us-east-1', 'US East'),
    ('us-west-1', 'US Oregon'),
    ('us-west-2', 'US Northern California'),
    ('eu-west-1', 'Ireland'),
    ('ap-southeast-1', 'Singapore'),
    ('ap-southeast-2', 'Sydney'),
    ('ap-northeast-1', 'Japan'),
    ('sa-east-1', 'Sao Paulo')
    )


EC2_REGIONS = firsts(EC2_REGIONS_CHOICES)

BACKING_STORES_CHOICES = (
    ('ebs', 'EBS'),
    ('instance-store', 'Instance-store')
    )

BACKING_STORES = firsts(BACKING_STORES_CHOICES)

PROJECT_STATES_CHOICES = (
    ('init', 'Initializing'),
    ('running', 'Running'),
    ('frozen', 'Frozen'),
    ('freezing', 'Freezing'),
    ('thawing', 'Thawing'),
    ('error', 'In error')
)

PROJECT_STATES = firsts(PROJECT_STATES_CHOICES)

TAG_FILTERS_CHOICES = (
    ('pick', 'Pick matching instances'),
    ('save', 'Save matching instances')
    )

TAG_FILTERS = firsts(TAG_FILTERS_CHOICES)

TAG_KEY_LENGTH_MAX = 127
TAG_VALUE_LENGTH_MAX = 255

INSTANCE_STATE_CHOICES = (
    ('pending', 'Pending'),
    ('running', 'Running'),
    ('shutting-down', 'Shutting down'),
    ('terminated', 'Terminated'),
    ('stopping', 'Stopping'),
    ('stopped', 'Stopped')
    )

INSTANCE_STATES = firsts(INSTANCE_STATE_CHOICES)

LOG_ENTRY_TYPES_CHOICES = (
    ('info', 'Informational'),
    ('exception', 'Program exception'),
    ('error', 'Error'),
    ('audit', 'Configuration changes')
    )

LOG_ENTRY_TYPES = firsts(LOG_ENTRY_TYPES_CHOICES)

class BaseModel(util.Logger, models.Model):
    """Just a common base model doing some mixins and stuff."""
    def __init__(self, *args, **kwargs):
        super(BaseModel, self).__init__(*args, **kwargs)

    def log_entry(self, message, type='info', details=None, user=None):
        """Create and save a log entry. Children of this class must
        define a method _log_entry that (at the least) will fill
        the corresponding log entry reference field (see LogEntry
        model for details)."""
        l = LogEntry(message=message, type=type, details=details, user=user)
        self._log_entry(l)
        l.save()

        self.log.info('%s: %s', l.type, l.message)

    class Meta:
        abstract = True

class Domain(BaseModel):
    """"Domain" is just a category for being one abstract "customer",
    holding many accounts. In the default mode with no authentication,
    there is only one domain, the "public" domain which doesn't have
    users defined (this is created in initial fixtures)."""

    # Name of the domain (short description)
    name = models.CharField(max_length=30)

    # DNS suffix
    domain = models.CharField(max_length=100)

    # Description for this domain
    description = models.TextField(blank=True)

    # Active?
    active = models.BooleanField(default=True)

    # Link to user that is the owner of this domain. Can be empty.
    owner = models.ForeignKey(auth.models.User,
                              related_name="owned_domains",
                              blank=True, null=True)

    def __unicode__(self):
        return self.name

    def _log_entry(self, l):
        l.domain = self

    class Meta:
        permissions = (
            ('domain_admin', 'Is domain admin'),
            )

class Account(BaseModel):
    # TODO: We really would want to add the AWS account ID here as
    # unique key, but getting it via API is stricly not possible,
    # although via a workaround it is. See here:
    # http://stackoverflow.com/questions/10197784/how-can-i-deduce-the-aws-account-id-from-available-basicawscredentials

    # Accounts always under a domain
    domain = models.ForeignKey('Domain', related_name='accounts')

    # Short descriptive name for the account
    name = models.CharField(max_length=255)

    # Access credentials for AWS
    access_key = models.CharField(max_length=60, unique=True)
    secret_key = models.CharField(max_length=60)

    # Is this account active?
    active = models.BooleanField(default=True)

    # When was the instance data last updated for this account
    updated = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return self.name + "/" + self.access_key

    # aws is argument here with a default so we can inject mock during
    # testing
    def __init__(self, *args, **kwargs):
        mate = kwargs.pop('mate', None)
        super(Account, self).__init__(*args, **kwargs)
        self.mate = mate

    def refresh(self, regions=None):
        """Refresh this account contents, updating list of tags,
        instances and EIPs in this account in the given `regions`. If
        `regions` is not specified, will go through `self.regions`."""

        if regions is None:
            regions = self.regions

        self.log.debug("refresh: %s, regions=%r", self, regions)

        if not self.mate:
            self.mate = aws.Account(self)

        total, added, deleted = 0, 0, 0
        started = timezone.now()

        for region in regions:
            try:
                with transaction.atomic():
                    (t, a, d) = self.mate.refresh_region(self, region)
                    self.updated = timezone.now()
                    self.save()
                    self.log.debug('%s: Done refresh with mate %r, updated %s, t/a/d %d/%d/%d', self, self.mate, self.updated, t, a, d)
                    total, added, deleted = total + t, added + a, deleted + d
            except IntegrityError:
                self.log.exception("Error while updating account %s in region %s",
                                   self, region)

            # TODO: catch other known exceptions from mate. As well in
            # there, convert those into known exceptions.

        elapsed = timezone.now() - started

        self.log_entry('Refreshed %d regions in %.2f seconds, total %d / added %d / deleted %d instances' % (
                len(regions), elapsed.seconds + elapsed.microseconds / 1e6, total, added, deleted))

        # Go through projects that are 'init' state and see if they
        # have any picked or saved instances --- then we move them to
        # "running" state.
        for project in self.projects.filter(state='init').all():
            if project.picked_instances or project.saved_instances:
                project.log_entry('Moving {0} from initializing to running state'.format(project))
                project.state = 'running'
                project.save()

    @property
    def regions(self):
        """Returns list of regions that should be checked for this
        account's activity. This list is constructed from the projects
        associated with this account. The result is useful for example
        in restricting queries only to regions that are relevant to
        this account."""
        all = [r for p in self.projects.all() for r in p.regions]
        return list(set(all))

    @property
    def instances(self):
        return self.instances.filter(account=self)

    def new_instance(self, **kwargs):
        """Create a new instance under this account."""
        return Instance(account=self, **kwargs)

    def new_project(self, **kwargs):
        """Create a new project under this account."""
        return Project(account=self, **kwargs)

    def _log_entry(self, l):
        l.account = self

class Tag(BaseModel):
    # Tag key
    key = models.CharField(max_length=TAG_KEY_LENGTH_MAX)

    # This is an abstract class only
    class Meta:
        abstract = True

    def __hash__(self):
        return self.key.__hash__()

    def __cmp__(self, other):
        return self.key.__cmp__(other.key)

class InstanceTag(Tag):
    # To instance ..
    instance = models.ForeignKey('Instance', related_name='tags')

    # And their tags have a value (which may be empty)
    value = models.CharField(max_length=TAG_VALUE_LENGTH_MAX)

    def __unicode__(self):
        return self.key + "=" + self.value

    def _log_entry(self, l):
        l.account = self.instance.account

class Instance(BaseModel):
    # Which account this instances has been retrieved from.
    account = models.ForeignKey('Account', related_name='instances')

    # Instance id. Note we don't make this primary_key (use the
    # integer id field instead) since instance ids are *not*
    # guaranteed to be unique over multiple regions.
    instance_id = models.CharField(max_length=30, validators=[validate_instance_id])

    # Instance type
    type = models.CharField(max_length=30)

    # Region this is running in .. in our model an account contains
    # instances from all (visited) regions. Filtered based on project
    # region.
    region = models.CharField(max_length=30, choices=EC2_REGIONS_CHOICES)

    # VPC instance is running in
    vpc_id = models.CharField(max_length=30, blank=True, null=True)

    # Type of backing store of the instance
    store = models.CharField(max_length=10, choices=BACKING_STORES_CHOICES)

    # Current instance state
    state = models.CharField(max_length=30, choices=INSTANCE_STATE_CHOICES)

    def __unicode__(self):
        return self.instance_id

    def new_tag(self, **kwargs):
        """Create a new tag under this instance."""
        return InstanceTag(instance=self, **kwargs)

    @property
    def environment(self):
        """Return an environment suitable for evaluating with
        freezr.filter.Filter.evaluate."""
        return {
            'region': self.region,
            'instance': self.instance_id,
            'type': self.type,
            'storage': self.store,
            'tags': {tag.key: tag.value for tag in self.tags.all()},
            }

    def __hash__(self):
        return self.instance_id.__hash__()

    def __cmp__(self, other):
        return self.instance_id.__cmp__(other.instance_id)

    def _log_entry(self, l):
        l.account = self.account

    class Meta:
        # Actually region + instance_id is unique, but we do not want
        # to leak information between domains. Conflicts within
        # domains are ok.
        unique_together = (('account', 'instance_id', 'region'))


class ElasticIp(BaseModel):
    # Which project this is from, note if multiple projects use the
    # same accont *without* vpcs, then the same EIP will be listed
    # multiple times (once for each project).
    project = models.ForeignKey('Project', related_name='elastic_ips')

    # Instance currently bound to, 0..1
    instance = models.ForeignKey('Instance', blank=True, null=True)

    # IP address itself
    address = models.CharField(max_length=20)

# Projects
class Project(BaseModel):
    # Project name
    name = models.CharField(max_length=255)

    # State of this project
    state = models.CharField(max_length=30, choices=PROJECT_STATES_CHOICES, default='init')

    # Always in a domain, utilizing one account (but multiple projects
    # may use the same account). Note that the domain is implicit, via
    # account, but we purposefully create a shortcut here for it.
    account = models.ForeignKey('Account', related_name='projects')

    @property
    def domain(self):
        return self.account.domain

    # Region where this project applies to, this is encoded as a char
    # field, below we have a property to allow setting and retrieving
    # this as a list.
    _regions = models.CharField(max_length=255, default=",".join(EC2_REGIONS))
    # Long description
    description = models.TextField(blank=True)

    # Pick filter
    pick_filter = models.TextField(blank=True, null=True)

    # Save filter
    save_filter = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return unicode(self.account) + "/" + self.name

    def filter_instances(self, filter_text):
        """Return a list of instances that match the `filter_text`
        filter pattern under the account of this project.

        Note that empty pattern will always return an empty list --
        this is to prevent empty fields from accidentally removing a
        lot of instances.. if you want to really match *all* instances
        under an account you'd have to write an always-true statement
        like "region = region"."""

        if not filter_text:
            return []

        f = filter.Filter(filter_text)
        picked = set()

        for instance in self.account.instances.all():
            self.log.debug("filter: looking at %s", instance)
            if f.evaluate(instance.environment):
                picked.add(instance)

        return list(picked)

    @property
    def picked_instances(self):
        return self.filter_instances(self.pick_filter)

    @property
    def saved_instances(self):
        return self.filter_instances(self.save_filter)

    @property
    def regions(self):
        if not self._regions:
            return []
        return self._regions.split(",")

    @regions.setter
    def regions(self, value):
        self._regions = list(set(value)).join(",")

    def _log_entry(self, l):
        l.project = self

    def freeze(self):
        if self.state != 'running':
            return

        self.log_entry('Starting to freeze project')
        self.log.debug("freeze: self=%r", self)

    def thaw(self):
        self.log.debug("thaw: self=%r", self)

    class Meta:
        permissions = (
            ('freeze_project', 'Can freeze linked project assets'),
            ('thaw_project', 'Can thaw linked project assets'),
            )

class ProjectGroupRelation(BaseModel):
    """Relation object telling what permission is connected to which
    Django Group object. This allows us to attach permissions to
    groups, which in turn are attached to an relation, which in turn
    is attached to a Project object.

    This means that a single group can have 0 or 1
    ProjectGroupRelations, which then has 1 Project association. To
    check which project the group is associated with fetch via
    `group.project_relation.project` (note that group.project_relation
    may be None).

    This cannot be done directly via group.project, since that would
    imply there is only one group per project, which isn't true. There
    may be multiple different groups. We could use ManyToMany, too,
    but I think this is more explicit. And besides, we can later
    attach additional information to this relation object, if
    needed."""
    project = models.ForeignKey('Project',
                                related_name='group_relations',
                                on_delete=models.CASCADE)

    group = models.OneToOneField(auth.models.Group,
                                 related_name='project_relation',
                                 on_delete=models.CASCADE)

    def _log_entry(self, l):
        l.project = self.project

class LogEntry(models.Model):
    # Entry type
    type = models.CharField(max_length=10, default='info', choices=LOG_ENTRY_TYPES_CHOICES)

    # Entry time
    time = models.DateTimeField(auto_now_add=True)

    # User who initiated the action, if applicable (may be null for
    # scheduled tasks, for example)
    user = models.ForeignKey(auth.models.User, on_delete=models.SET_NULL, blank=True, null=True, related_name='+log_entries')

    # Main entry message text, should never be empty
    message = models.TextField()

    # Additional details, may be empty
    details = models.TextField(blank=True, null=True)

    # System error flag .. this is used for two things, first, system
    # errors are not normally shown for regular users, and
    # secondarily, syste errors may have domain, account and project
    # set to None (which normally shouldn't happen).
    system_error = models.BooleanField(default=False)

    # Finally, a single log entry may be under either a domain,
    # account or project. Only *ONE* of these should be set at any
    # point (OTOH, we don't enforce that at the model level) so that
    # the delete cascade works correctly.
    domain = models.ForeignKey('Domain', blank=True, null=True, related_name="log_entries", on_delete=models.CASCADE)
    account = models.ForeignKey('Account', blank=True, null=True, related_name="log_entries", on_delete=models.CASCADE)
    project = models.ForeignKey('Project', blank=True, null=True, related_name="log_entries", on_delete=models.CASCADE)

    def __unicode__(self):
        return "{0} {1}: {2} ({3})".format(self.time, self.type, self.message,
                                         self.domain or self.account or self.project)

    def set_object(self, obj):
        """Utility routine that tries to set `obj` to the correct slot,
        either `domain`, `account` or `project`. If none matches,
        does nothing."""
        if isinstance(obj, Domain):
            self.domain = obj
        elif isinstance(obj, Account):
            self.account = obj
        elif isinstance(obj, Project):
            self.project = obj

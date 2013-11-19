from django.db import models
from django.core.validators import validate_slug
from django.core.exceptions import ValidationError
import re

VALID_INSTANCE_RE = re.compile(r'^i-[0-9a-f]+$')

def validate_instance_id(value):
    if not VALID_INSTANCE_RE.match(value):
        raise ValidationError(u'%s is not a valid instance id' % value)

def firsts(elts):
    return map(lambda e: e[0], elts)

# Should get this dynamically from AWS instead
EC2_REGIONS_CHOICES = (
    ('eu-west-1', 'Ireland'),
    ('us-east-1', 'US East'),
    ('ap-northeast-1', 'Japan')
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
    ('freeze', 'Freezing'),
    ('thaw', 'Thawing'),
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

# "Domain" is just a category for being one abstract "customer",
# holding many accounts. In the default mode with no authentication,
# there is only one domain, the "public" domain which doesn't have
# users defined (this is created in initial fixtures).

class Domain(models.Model):
    # Name of the domain (short description)
    name = models.CharField(max_length=30)

    # DNS suffix
    domain = models.CharField(max_length=100)

    # Description for this domain
    description = models.TextField(blank=True)

    # Active?
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

class Account(models.Model):
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
    updated = models.DateField(blank=True, null=True)

    def __unicode__(self):
        return unicode(self.domain) + "/" + self.access_key

    def refresh(self, regions=EC2_REGIONS):
        """Refresh this account contents, updating list of tags,
        instances and EIPs in this account in the given regions."""
        print("{0}.refresh: regions={1!r}".format(self, regions))

class Tag(models.Model):
    # Tag key
    key = models.CharField(max_length=TAG_KEY_LENGTH_MAX)

    # This is an abstract class only
    class Meta:
        abstract = True

# We don't represent account tags separately. Find
# account.instances*.tags instead.

# class AccountTag(Tag):
#     # Tags to an account ..
#     account = models.ForeignKey('Account')

class InstanceTag(Tag):
    # and to instances ..
    instance = models.ForeignKey('Instance', related_name='tags')

    # And their tags have a value (which may be empty)
    value = models.CharField(max_length=TAG_VALUE_LENGTH_MAX)

    def __unicode__(self):
        return self.key + "=" + self.value

# class TagFilter(Tag):
#     # Project this filter applies to
#     project = models.ForeignKey('Project', related_name='filters')

#     # Selector value. Currently just a simple equals comparison.
#     value = models.CharField(max_length=TAG_VALUE_LENGTH_MAX, blank=True, null=True)

#     # Type of filter, either pick or save
#     type = models.CharField(max_length=10, choices=TAG_FILTERS_CHOICES)

#     def __unicode__(self):
#         return self.key + "~" + self.value

#     # class Meta:
#     #     abstract = True

# class InstanceTagFilter(TagFilter):
#     project = models.ForeignKey('Project', related_name='instance_filters')

# class SaveTagFilter(TagFilter):
#     project = models.ForeignKey('Project', related_name='save_filters')

class Instance(models.Model):
    # Instance id. Note we don't make this primary_key (use the
    # integer id field instead) since instance ids are *not*
    # guaranteed to be unique over multiple regions.
    instance_id = models.CharField(max_length=30, validators=[validate_instance_id])

    # Region this is running in .. in our model an account contains
    # instances from all (visited) regions. Filtered based on project
    # region.
    region = models.CharField(max_length=30, choices=EC2_REGIONS_CHOICES)

    # VPC instance is running in
    vpc_id = models.CharField(max_length=30, blank=True, null=True)

    # Type of backing store of the instance
    store = models.CharField(max_length=10, choices=BACKING_STORES_CHOICES)

    def __unicode__(self):
        return self.instance_id

class ElasticIp(models.Model):
    # Which project this is from, note if multiple projects use the
    # same accont *without* vpcs, then the same EIP will be listed
    # multiple times (once for each project).
    project = models.ForeignKey('Project', related_name='elastic_ips')

    # Instance currently bound to, 0..1
    instance = models.ForeignKey('Instance', blank=True, null=True)

    # IP address itself
    address = models.CharField(max_length=20)

# Projects
class Project(models.Model):
    # State of this project
    state = models.CharField(max_length=30, choices=PROJECT_STATES_CHOICES, default='init')

    # Always in a domain, utilizing one account (but multiple projects
    # may use the same account). Note that the domain is implicit, via
    # account, but we purposefully create a shortcut here for it.
    account = models.ForeignKey('Account', related_name='projects')

    @property
    def domain(self):
        return self.account.domain

    # Region where this project applies to
    region = models.CharField(max_length=30, choices=EC2_REGIONS_CHOICES)

    # VPC id where to narrow this project scope to
    vpc_id = models.CharField(max_length=30, blank=True, null=True)

    # Project name and description
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Pick filter
    pick_filter = models.TextField(blank=True, null=True)

    # Save filter
    save_filter = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return unicode(self.account) + "/" + self.name

# -*- tab-width: 2 -*-

# For REST check http://eviltrout.com/2013/03/23/ember-without-data.html

# JSONTransforms.array from http://stackoverflow.com/a/13884238/779129
Transforms = {}
Transforms.array = DS.Transform.extend
  # If the outgoing json is already a valid javascript array
  # then pass it through untouched. In all other cases, replace it
  # with an empty array.  This means null or undefined values
  # automatically become empty arrays when serializing this type.

  serialize: (jsonData)->
    if Em.typeOf(jsonData) is 'array' then jsonData else []

  # If the incoming data is a javascript array, pass it through.
  # If it is a string, then coerce it into an array by splitting
  # it on commas and trimming whitespace on each element.
  # Otherwise pass back an empty array.  This has the effect of
  # turning all other data types (including nulls and undefined
  # values) into empty arrays.

  deserialize: (externalData)->
    switch Em.typeOf(externalData)
      when 'array'  then return externalData
      when 'string' then return externalData.split(',').map((item)-> jQuery.trim(item))
      else               return []

# modelled based on previous
Transforms.map = DS.Transform.extend
  serialize: (jsonData)->
    console?.log "map.serialize", jsonData
    if Em.typeOf(jsonData) is 'object' then jsonData else {}

  deserialize: (externalData)->
    console?.log "map.deserialize", externalData
    ary2obj = (ary) ->
      obj = {}
      for item in ary
        obj[item[0]] = item[1] if item[1]?
      obj
    switch Em.typeOf(externalData)
      when 'object' then return externalData
      when 'string' then return ary2obj externalData.split(',').map((item)-> jQuery.trim(item).split(":"))
      else               return {}

# from
# http://blog.matthias-reining.com/handlebarsjs-how-to-iterate-over-a-map/,
# modified for coffeescript
#
Handlebars.registerHelper 'eachMapEntries', (context, options) ->
    console?.log "context", context
    ret = ""
    $.each context, (key, value) ->
        ret = ret + options.fn {"key": key, "value": value}
    ret

yearMinutes = 365 * 24 * 60
dayMinutes = 24 * 60
hourMinutes = 60

Handlebars.registerHelper 'timeSince', (property, options) ->
  time = new Date(Ember.get(this, property))
  now = new Date()

  delta = Math.round((now - time) / 1e3 / 60)
  parts = []
  if delta >= yearMinutes
    parts.push "" + Math.floor(delta / yearMinutes) + " years"
    delta = delta % yearMinutes
  if delta >= dayMinutes
    parts.push "" + Math.floor(delta / dayMinutes) + " days"
    delta = delta % dayMinutes
  if delta >= hourMinutes and parts.length < 2
    parts.push "" + Math.floor(delta / hourMinutes) + " hours"
    delta = delta % hourMinutes
  if delta > 0 and parts.length < 2
    parts.push "" + Math.floor(delta) + " minutes"

  if parts.length == 0
    return "just now"

  return parts.join(", ")


########################################################################
#
# freezr.coffee
#

url = (p) -> freezr_api_root + p

window.App = App = Ember.Application.create
  LOG_TRANSITIONS: true

App.register 'transform:array', Transforms.array
App.register 'transform:map', Transforms.map

# DS.DjangoRESTSerializer = DS.DjangoRESTSerializer.extend
#   patchInJSONRoot: () ->
#     console?.log "here, patchInJSONRoot"
#     return []

#   extract: () ->
#     console?.log "here, extract"
#     return []

# App.DefaultSerializer = DS.DjangoRESTSerializer.extend
#   extract: () ->
#     dsoifsjiofosd

# App.Adapter = DS.DjangoRESTAdapter.extend
#   namespace: 'api'
#   pathForType: (type) ->
#     console?.log "pathForType: type", type
#     return type
#   defaultSerializer: "App/Default"
# #  serializer: new App.DefaultSerializer()
#   serializer: new DS.DjangoRESTSerializer()
#   extract: () ->
#     console?.log "extract"
#     return []

# DS.DjangoRESTAdapter = DS.DjangoRESTAdapter.extend
#   # no plurarizations, all are base type names

# App.reopen
#   ApplicationAdapter: DS.DjangoRESTAdapter.extend
#     namespace: 'api'
#     pathForType: (type) -> type + "/"

App.reopen
  ApplicationAdapter: DS.FixtureAdapter.extend {}

# App.reopen
#   ApplicationAdapter: DS.DjangoRESTAdapter.extend
#     namespace: 'api'
#     pathForType: (type) -> type

App.Domain = DS.Model.extend
  name: DS.attr('string')
  description: DS.attr('string')
  domain: DS.attr('string')
  accounts: DS.hasMany('account')
  active: DS.attr('boolean')
  logEntries: DS.attr('array')

App.Account = DS.Model.extend
  name: DS.attr('string')
  description: DS.attr('string')
  projects: DS.hasMany('project')
  domain: DS.belongsTo('domain')
  active: DS.attr('boolean')
  updated: DS.attr('date')
  regions: DS.attr('array')
  logEntries: DS.attr('array')
  accessKey: DS.attr('string')
  instances: DS.hasMany('instance')

App.Project = DS.Model.extend
  name: DS.attr('string')
  description: DS.attr('string')
  state: DS.attr('string')
  account: DS.belongsTo('account')
  pickFilter: DS.attr('string')
  saveFilter: DS.attr('string')
  terminateFilter: DS.attr('string')
  logEntries: DS.attr('array')
  pickedInstances: DS.hasMany('instance')
  savedInstances: DS.hasMany('instance')
  terminatedInstances: DS.hasMany('instance')
  skippedInstances: DS.hasMany('instance')
  stateChanged: DS.attr('date')
  regions: DS.attr('array')
  isRunning: (() -> (@get 'state') == 'running').property('state')
  isFrozen: (() -> (@get 'state') == 'frozen').property('state')
  canChange: (() -> (@get 'state') in ['running', 'frozen', 'error']).property('state')
  canFreeze: (() -> (@get 'isRunning')).property('state')
  canThaw: (() -> (@get 'isFrozen')).property('state')
  cannotChange: (() -> not (@get 'canChange')).property('state')

App.Instance = DS.Model.extend
  instanceId: DS.attr('string')
  account: DS.belongsTo('account')
  region: DS.attr('string')
  vpcId: DS.attr('string')
  storageType: DS.attr('string')
  state: DS.attr('string')
  tags: DS.attr('map')

App.Domain.FIXTURES = [
  {
    id: 1
    name: 'Sample domain'
    description: ''
    domain: 'test.local'
    accounts: [1]
    active: true
    logEntries: []
  }]

App.Account.FIXTURES = [
  {
    id: 1
    name: 'Sample account'
    description: ''
    projects: [1, 2]
    domain: 1
    active: true
    updated: '2013-12-06T16:47:20+02:00'
    regions: ['us-east-1']
    logEntries: []
    accessKey: '123456'
    instances: [1, 2, 3]
  }]

App.Project.FIXTURES = [
  {
    id: 1
    name: 'Project 1'
    description: 'long project description with potentially lots of text\nand also in multiple paragraphs'
    state: 'running'
    account: 1
    pickFilter: 'region = "us-east-1"'
    saveFilter: 'true'
    terminateFilter: ''
    logEntries: []
    pickedInstances: [1,2]
    savedInstances: [2]
    terminatedInstances: [1]
    skippedInstances: []
    stateChanged: '2013-12-05T20:47:20+02:00'
    regions: ['us-east-1', 'us-west-1']
  },
  {
    id: 2
    name: 'Project 2'
    description: ''
    state: 'frozen'
    account: 1
    pickFilter: 'region = "us-west-1"'
    saveFilter: 'true'
    terminateFilter: ''
    logEntries: []
    pickedInstances: [3]
    savedInstances: [3]
    terminatedInstances: []
    skippedInstances: []
    stateChanged: '2013-11-01T00:00:00+02:00'
    regions: ['us-east-1', 'us-west-1']
  }]

App.Instance.FIXTURES = [
  {
    id: 1
    instanceId: 'i-12345'
    account: 1
    region: 'us-east-1'
    vpcId: '',
    storageType: 'ebs'
    state: 'stopped'
    tags: {Name: 'jenkins'}
  },
  {
    id: 2
    account: 1
    instanceId: 'i-23456'
    region: 'us-east-1'
    vpcId: null,
    storageType: 'instance-store'
    state: 'running'
    tags: {Name: 'slave01'}
  },
  {
    id: 3
    account: 1
    instanceId: 'i-34567'
    region: 'us-west-1'
    vpcId: null,
    storageType: 'ebs'
    state: 'running'
    tags: {Name: 'staging01'}
  }]

App.Router.map () ->
  @resource 'home', { path: "/home" }
  @resource 'projects', { path: "/projects" }, () ->
    @resource 'project', { path: '/:project_id' }, () ->
      @route 'edit'
    @route 'new', { path: "/new" }
  @resource 'accounts', { path: "/accounts" }, () ->
    @resource 'account', { path: '/:account_id' }, () ->
      @route 'edit'
    @route 'new', { path: "/new" }

App.ProjectsController = Ember.Controller.extend {}

App.ProjectController = Ember.ObjectController.extend {}

  # isExpanded: false
  # actions:
  #   expand: () -> this.set 'isExpanded', true
  #   collapse: () -> this.set 'isExpanded', false

App.ProjectsIndexController = Ember.ObjectController.extend
  actions:
    thaw: () ->
      console?.log "thaw", arguments
    freeze: () ->
      console?.log "freeze", arguments

App.ProjectsProjectView = Ember.View.extend
  templateName: 'projects-project'
  expanded: false
  actions:
    expand: () -> this.set 'expanded', true
    collapse: () -> this.set 'expanded', false

  didInsertElement: () ->
    console?.log "didInsertElement"
    @$('.dropdown-toggle').dropdown()

App.ProjectsProjectController = Ember.ObjectController.extend
  isRunning: true

App.IndexRoute = Ember.Route.extend
  redirect: () -> @transitionTo 'projects'

allRoute = Ember.Route.extend
  model: () ->
    {
      domains: this.store.find('domain')
      accounts: this.store.find('account')
      projects: this.store.find('project')
      instances: this.store.find('instance')
    }

App.HomeRoute = allRoute.extend {}
App.ProjectsIndexRoute = allRoute.extend {}

$ ->
  $(".project-list .project-info").each (index, el) ->
    $(el).find('.project-info-expand a').click () ->
      $(el).find('.project-info-long').toggle()
      $(el).find('.project-info-expand a').toggle()

  actionColumnVisible = false

  $('.project-action-expand').click () ->
    actionColumnVisible = not actionColumnVisible

    if actionColumnVisible
      $('.project-shrinker').removeClass('col-sm-10').addClass('col-sm-8')
    else
      $('.project-shrinker').removeClass('col-sm-8').addClass('col-sm-10')

    $('.project-expander').toggle(actionColumnVisible)
    $('.project-action-expand a').toggle()

  # $('.dropdown-toggle').dropdown()

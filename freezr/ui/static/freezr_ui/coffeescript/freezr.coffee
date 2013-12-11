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
    #console?.log "map.deserialize", externalData
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
    return "only a while"

  return parts.join(", ")


########################################################################
#
# freezr.coffee
#

url = (p) -> freezr_api_root + p

window.App = App = Ember.Application.create
  LOG_TRANSITIONS: true
  LOG_TRANSITIONS_INTERNAL: true
  LOG_VIEW_LOOKUPS: true
  LOG_BINDINGS: true
  LOG_ACTIVE_GENERATION: true

# modeled from https://github.com/jgwhite/ember-time
App.FromNowView = Ember.View.extend
  nextTick: null
  tagName: 'time'
  template: Ember.Handlebars.compile '{{view.output}}'
  output: (() -> (moment @get('value')).fromNow(true)).property('value')
  tick: () ->
    @nextTick = Ember.run.later this, (() ->
      @notifyPropertyChange('output')
      @tick()), 1000
  willDestroyElement: () ->
    Ember.run.cancel @nextTick
  didInsertElement: () -> @tick()

Handlebars.registerHelper 'fromNow', App.FromNowView

Ember.RSVP.configure 'onerror', (error) ->
    Ember.Logger.assert(false, error)

Ember.run.backburner.debug = true

App.register 'transform:array', Transforms.array
App.register 'transform:map', Transforms.map

App.FreezrSerializer = DS.RESTSerializer.extend
  extractSingle: (store, type, payload) ->
    normalized = @normalizePayload type, payload
    serializer = store.serializerFor(type)
    ret = serializer.normalize(type, normalized, type.typeKey)
    return ret

  extractArray: (store, type, payload) ->
    return (@extractSingle(store, type, elt) for elt in payload)

  attributeKeys:
    'storageType': 'store'

  # Can't use "store" as key in model, it conflicts with Ember's own
  # .store field. Rename from JSON response 'store' to 'storageType'
  # field. Also, decamelize keys otherwise.
  keyFor: (attr) ->
    if attr of @attributeKeys
      return @attributeKeys[attr]
    Ember.String.decamelize(attr)

  keyForAttribute: (attr) -> @keyFor(attr)
  keyForRelationship: (attr, relationship) -> @keyFor(attr)

App.FreezrAdapter = DS.RESTAdapter.extend
  serializer: new App.FreezrSerializer()
  defaultSerializer: "App/Freezr"

  pathForType: (type) ->
    return type

App.reopen
  ApplicationAdapter: App.FreezrAdapter.extend
    namespace: "api"

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
  stateUpdated: DS.attr('date')
#  stateUpdated: DS.attr('string')
  regions: DS.attr('array')
  isRunning: (() -> (@get 'state') == 'running').property('state')
  isFrozen: (() -> (@get 'state') == 'frozen').property('state')
  isFreezing: (() -> (@get 'state') == 'freezing').property('state')
  isThawing: (() -> (@get 'state') == 'thawing').property('state')
  canChange: (() -> (@get 'state') in ['running', 'frozen', 'error']).property('state')
  canFreeze: (() -> (@get 'isRunning')).property('state')
  canThaw: (() -> (@get 'isFrozen')).property('state')
  cannotChange: (() -> not (@get 'canChange')).property('state')

  currentTransientStateReloader: null

  transientStateReload: (() ->
    console?.log @toString(), "state", @get('state'), "when", @get('stateUpdated'), "otherwhen", @store.getById('project', @get('id')).get('stateUpdated')
    if @currentTransientStateReloader?
      Ember.run.cancel @currentTransientStateReloader
      @currentTransientStateReloader = null

    if not (@get('state') in ['running', 'frozen'])
      @currentTransientStateReloader = \
        Ember.run.later this, (() ->
          console?.log "triggering reload"
          @reload()), 5000
    ).observes('state', 'stateUpdated').on('didLoad')

  printstate: ((obj, key) ->
    console?.log "state:", @get('state'), "stateUpdated", @get('stateUpdated'), "obj", obj, "key", key
    console?.log "obj.get(stateUpdated)", obj.get('stateUpdated')
    console?.log "obj.get(state)", obj.get('state')
  ).observes('state', 'stateUpdated')

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
    stateUpdated: '2013-12-05T20:47:20+02:00'
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
    stateUpdated: '2013-11-01T00:00:00+02:00'
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

App.ProjectsIndexView = Ember.View.extend
  actionsVisible: true
  actions:
    expand: () -> @set('actionsVisible', true)
    collapse: () -> @set('actionsVisible', false)

App.ProjectsIndexController = Ember.ObjectController.extend
  refreshingAll: false
  refreshingCount: 0
  refreshCount: (delta) ->
    if delta?
      @refreshingCount += delta
    console?.log "count", @refreshingCount
    if @refreshingCount == 0
      @set('refreshingAll', false)
    else
      @set('refreshingAll', true)

  operate: (project, operation) ->
      $.ajax
        url: '/api/project/' + project.id + '/' + operation + '/'
        type: 'POST'

        fail: () =>
          console?.log "operation fail", arguments

        success: (payload) =>
          console?.log "operation success", arguments
          project.reload()

  actions:
    thaw: (project) ->
      console?.log "thaw", arguments
      @operate project, 'thaw'

    freeze: (project) ->
      console?.log "freeze", arguments
      @operate project, 'freeze'

    edit: (project) ->
      console?.log "edit", arguments

    refresh: (project) ->
      project.reload()

    refreshAll: () ->
      modelNames = ['domain', 'account', 'project', 'instance']

      # We count model classes themselves to the refresh count. This
      # ensures that @refreshingCount > 0 until *all* models have been
      # found (.find).

      @refreshCount modelNames.length
      @set 'refreshingAll', true

      for modelName in modelNames
        do (modelName) =>
          @store.find(modelName).then (objs) =>
            objs = objs.toArray()
            @refreshCount objs.length
            for obj in objs
              # TODO: does this handle errors too?
              obj.reload().then () =>
                @refreshCount -1
            @refreshCount -1

    deactivate: (project) ->
      console?.log "deactivate", arguments

    create: () ->
      console?.log "create", arguments


App.ProjectsProjectView = Ember.View.extend
  templateName: 'projects-project'
  expanded: false
  actions:
    expand: () -> @set 'expanded', true
    collapse: () -> @set 'expanded', false

  didInsertElement: () ->
    #console?.log "didInsertElement"
    @$('.dropdown-toggle').dropdown()

App.ProjectsProjectController = Ember.ObjectController.extend
  isRunning: true

App.ActionsExpanderComponent = Ember.Component.extend
  actions:
    expand: () ->
      debugger

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

# $ ->
#   $(".project-list .project-info").each (index, el) ->
#     $(el).find('.project-info-expand a').click () ->
#       $(el).find('.project-info-long').toggle()
#       $(el).find('.project-info-expand a').toggle()

#   actionColumnVisible = false

#   $('.project-action-expand').click () ->
#     actionColumnVisible = not actionColumnVisible

#     if actionColumnVisible
#       $('.project-shrinker').removeClass('col-sm-10').addClass('col-sm-8')
#     else
#       $('.project-shrinker').removeClass('col-sm-8').addClass('col-sm-10')

#     $('.project-expander').toggle(actionColumnVisible)
#     $('.project-action-expand a').toggle()

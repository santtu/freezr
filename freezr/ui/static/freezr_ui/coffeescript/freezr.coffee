#
# freezr.coffee

url = (p) -> freezr_api_root + p

$ ->
  $('#output').text "Hello, world!"
  $.ajax url('/project/'),
    accept: "application/json"
    success: (data, status, xhr) ->
      $('#output').empty().append t = $('<table class="table"/>')
      t.append $('<thead><th>State</th><th>Project name</th></thead>')
      t.append tb = $('<tbody/>')
      for p in data
        tb.append (r = $('<tr/>'))
        r.append $('<td/>').text(p.state)
        r.append $('<td/>').text(p.name)

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

  $('.dropdown-toggle').dropdown()

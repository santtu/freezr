#!/bin/bash -e
#    set-window-option -g remain-on-exit on \; \
#    split-window "celery --autoreload -A freezr worker -l info -C" \; \
#    set-window-option -g synchronize-panes on \; \
top_dir=$(dirname $0)
app_dir=$top_dir/freezr
env="source $top_dir/virtualenv/bin/activate &&"
nw=new-window
tmux \
    start-server \; \
    set-window-option -g remain-on-exit on \; \
    bind-key r respawn-pane -k \; \
    bind-key k kill-window \; \
    new-session -s freezr "rabbitmq-server" \; \
    $nw "$env cd $app_dir && python manage.py celeryd --autoreload -B -E -l debug" \; \
    $nw "$env cd $app_dir && python manage.py runserver" \; \
    select-layout even-vertical
exit $?

#!/bin/bash -e
#    set-window-option -g remain-on-exit on \; \
#    split-window "celery --autoreload -A freezr worker -l info -C" \; \
#    set-window-option -g synchronize-panes on \; \
top_dir=$(dirname $0)
app_dir=$top_dir
nw=new-window
export DJANGO_SETTINGS_MODULE=freezr.app.settings.development
if [[ $(uname) = Darwin ]]; then
    rabbitmqserver="rabbitmq-server"
else
    rabbitmqserver="sudo service rabbitmq-server status || sudo service rabbitmq-server start; echo 'Everything is fine even if this \"pane is dead\".'"
fi
if [[ -n "$VIRTUAL_ENV" && -r "$VIRTUAL_ENV/bin/activate" ]]; then
    env=". $VIRTUAL_ENV/bin/activate && "
else
    env=""
fi
tmux \
    start-server \; \
    set-window-option -g remain-on-exit on \; \
    bind-key r respawn-pane -k \; \
    bind-key k kill-window \; \
    new-session -n 'rabbitmq-server' -s freezr "echo '###### rabbitmq-server'; $rabbitmqserver" \; \
    $nw -n 'celeryd' "echo '###### celeryd'; $env cd $app_dir && (pids=\$(cat celeryd.pid 2>/dev/null); [ -n \"\$pids\" ] && kill -9 \$pids; python manage.py celeryd --concurrency=1 -B -l debug --pidfile celeryd.pid 2>&1 | tee celeryd.log)" \; \
    $nw -n 'runserver' "echo '###### runserver'; $env cd $app_dir && python manage.py runserver -v2 0.0.0.0:8000 2>&1 | tee runserver.log" \; \
    select-layout even-vertical
exit $?

# -*- coding: utf-8 -*-
# =====================
# Автоматизация деплоя не тестовый стенд
# =====================
from invoke import Responder
from fabric import Connection

PROJECT_PREFIX = 'gnc_test'
BRANCH = 'dev_gnc'  # hitsl.configurations
USER_NAME = 'USER_NAME'
USER_PASS = 'USER_PASS'
CONNECTION_NAME = 'gnc_test'
SERVER_PASS = 'SERVER_PASS'

stash_login = Responder(
    pattern="Username for 'https://stash.my-repo.ru':",
    response="{}\n".format(USER_NAME),
)
stash_pass = Responder(
    pattern="Password for 'https://{}@stash.my-repo.ru':".format(USER_NAME),
    response="{}\n".format(USER_PASS),
)
sudo_pass = Responder(
    pattern=r"\[sudo\] password for tmis:",
    response="{}\n".format(SERVER_PASS),
)

c = Connection(CONNECTION_NAME)
with c.cd('/srv/{}/'.format(PROJECT_PREFIX)):
    c.run('git checkout {}'.format(BRANCH), pty=True)
    c.run('./update-apps.sh', pty=True, watchers=[stash_login, stash_pass])
    c.run('./{}_restart_app.sh'.format(PROJECT_PREFIX), pty=True, watchers=[sudo_pass])

print('Done!')

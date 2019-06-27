# -*- coding: utf-8 -*-
# =====================
# Скрипт выводит список коммитов, которые попадут в следующую сборку
# =====================
import re

from subprocess import check_output


class RLS(object):
    """ReleaseLatestCommits - последний коммит вошедший в релиз"""
    hippo = '8c504098b8c'
    nemesis = '6f1e12e2c7e'
    caesar = '49305db61b7'
    hitsl_conf = '412919f4707'


def get_commits(start_hash, proj_path='.'):
    title_raw = check_output("""git log {0}.. --pretty=format:'%s'""".format(start_hash),
                             cwd=proj_path, shell=True)
    title_list = title_raw.splitlines()

    def find_commit_name(s):
        return map(lambda x: x.upper(), re.findall(r'(TMIS-\d+|RIMIS-\d+)', s, re.I))

    result = set()
    for title in title_list:
        commit_names = find_commit_name(title)
        result.update(set(commit_names) or {title})

    return result


result = set()
result.update(get_commits(RLS.hippo, 'code/hippocrates'))
result.update(get_commits(RLS.nemesis, 'code/nemesis'))
result.update(get_commits(RLS.caesar, 'code/caesar'))
result.update(get_commits(RLS.hitsl_conf))

for i in sorted(result):
    print i

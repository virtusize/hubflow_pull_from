#!/usr/bin/env python
"""
Detect branch for deployment automtically.

Usage:
  pull_from -h | --help
  pull_from [--verbose] --repo <repository> --token <token>

Options:
  -h, --help              Show this help.
  -t, --token <token>     Github API application access token
  -r, --repo <repository> Github repository
  -v, --verbose           Verbose mode.


Examples:

  pull_from -r 'virtusize/cloud_v2' -t fgji3tydvehehf

"""

import requests
import arrow
from docopt import docopt
import re

# import httplib as http_client
# http_client.HTTPConnection.debuglevel = 1


def latest_commit(api_url, branch, headers, since=0):
    if since:
        url = '{}/commits?sha={}&since={}'.format(api_url, branch, since)
    else:
        url = '{}/commits?sha={}'.format(api_url, branch)
    r = requests.get(url, headers=headers)
    if (r.ok):
        commits = r.json()
        latest = 0
        for c in commits:
            ts = commit_timestamp(c['url'], headers=headers)
            if ts > latest:
                latest = ts
                commit = c
        return commit


def commit_timestamp(url, headers):
    r = requests.get(url, headers=headers)
    if (r.ok):
        commit_obj = r.json()
        d = arrow.get(commit_obj['commit']['committer']['date'])
        return d.timestamp


def repo_normalization(name):
    if name:
        regex = r'(?:git@|https?:/+)?(?:github\.com)?[:/]?(.*?)(?:.git)?$'
        m = re.search(regex, name)
        if m:
            return m.group(1)


def main():
    arguments = docopt(__doc__, version='0.0.1')
    api_token = arguments.get('--token', None)
    if not api_token:
        print "Invalid api token"
        return 1
    headers = {'Authorization': 'token %s' % api_token}

    repo = arguments.get('--repo', None)
    repo = repo_normalization(repo)

    if not repo:
        print "Invalid repository"
        return 1

    api_url = 'https://api.github.com/repos/%s' % repo

    pull_from = {}

    r = requests.get(api_url, headers=headers)
    if (r.ok):
        r = requests.get(api_url + '/branches', headers=headers)
        if (r.ok):
            branches = r.json()
            print "Branches: ", ", ".join([b['name'] for b in branches])
            # there are many commits in a 'master' branch
            week = arrow.utcnow().replace(weeks=-1)
            # timestamp should be in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.
            since = week.format('YYYY-MM-DDTHH:mm:ss') + 'Z'
            commit_obj = latest_commit(api_url, 'master', since=since,
                                        headers=headers)
            master_date = arrow.get(commit_obj['commit']['committer']['date'])
            # print "MASTER DATE ", master_date
            pull_from['branch'] = 'master'
            pull_from['date'] = master_date

            releases = [b for b in branches if 'release/' in b['name']]
            hotfixes = [b for b in branches if 'hotfix/'  in b['name']]

            if releases:
                print "Releases: ", ", ".join([b['name'] for b in releases])
                b = sorted(releases, key=lambda k: k['name'])[-1]
                commit_obj = latest_commit(api_url, b['name'], headers=headers)
                b_date = arrow.get(commit_obj['commit']['committer']['date'])
                # print "REL DATE", b_date
                if (b_date - pull_from['date']).seconds > 0:
                    pull_from['branch'] = b['name']
                    pull_from['date'] = b_date

            if hotfixes:
                print "Hotfixes: ", ", ".join([b['name'] for b in hotfixes])
                b = sorted(hotfixes, key=lambda k: k['name'])[-1]
                commit_obj = latest_commit(api_url, b['name'], headers=headers)
                b_date = arrow.get(commit_obj['commit']['committer']['date'])
                #  print "FIX DATE", b_date
                if (branch_date - pull_from['date']).seconds > 0:
                    pull_from['branch'] = b['name']
                    pull_from['date'] = b_date

            print "Pull from ", pull_from['branch']

        else:
            print "Repository is not exist or not available"
            return(2)
    else:
        print r.text
        return(1)

if __name__ == '__main__':
    main()

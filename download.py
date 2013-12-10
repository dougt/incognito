import json
import stat
import time
import os
import codecs
import re
from getpass import getpass

from pyquery import PyQuery
from PIL import Image
import requests

MOZLDAP = 'http://localhost:8000/employee/?mail={email}'
URL = 'https://phonebook.mozilla.org//pic.php?mail={email}'
EXCEPTIONS = (
    'jabbatest@mozilla.com',
)
username = password = None

#url = '#search/mitchell@mozilla.com'

def download(url):
    global username
    if not username:
        username = raw_input('LDAP Email: [pbengtsson@mozilla.com]')
        #if not username:
        #    username = 'pbengtsson@mozilla.com'
    global password
    if not password:
        password = getpass('Password: ')
        assert password

    r = requests.get(url, auth=(username, password))
    assert r.status_code == 200, r.status_code
    return r

def find_emails(html):
    regex = re.compile('#search/(\w+@(mozilla\.com|mozillafoundation\.org))')
    point = html.find('People who need to set their manager')
    emails = [x[0] for x in regex.findall(html)]
    for email in emails:
        p = html.find(email)
        if p < point:
            yield email

def find_people(html):
    doc = PyQuery(html)
    point = html.find('People who need to set their manager')
    for a in doc('a.hr-link'):
        href = a.attrib['href']
        if href.startswith('#search/'):
            email = href.replace('#search/', '')
            if html.find(email) > point:
                continue
            yield (email, a.text)

    """
    regex = re.compile('#search/(\w+@(mozilla\.com|mozillafoundation\.org))')
    point = html.find('People who need to set their manager')
    emails = [x[0] for x in regex.findall(html)]
    for email in emails:
        p = html.find(email)
        if p < point:
            yield (email, name)
    """


def histogram(filename):
    img = Image.open(filename)
    return ''.join(str(x) for x in img.histogram())

def histograms(emails):
    for e in emails:
        print histogram(e+'.jpg')

def cli(emails):

    for email in emails:
        url = URL.format(email=email)
        r = download(url)
        #print r.text
        assert r.status_code == 200, r.status_code
        print r.headers['content-type']
        filename = '%s.jpg' % email
        with open(filename, 'wb') as f:
            f.write(r.content)

        print "wrote", filename

"""
if __name__ == '__main__':
    import sys
    if not sys.argv[1:]:
        print "USAGE: %s some@email.com [other@email.com] ..." % __file__
        sys.exit(1)
    histograms(sys.argv[1:])
    cli(sys.argv[1:])
"""

def run():
    dest = 'download'
    if not os.path.isdir(dest):
        os.mkdir(dest)

    _tree_filename = os.path.join(dest, 'tree.html')
    try:
        html = codecs.open(_tree_filename, 'r', 'utf-8').read()
    except IOError:
        html = download('https://phonebook.mozilla.org/tree.php').text
        codecs.open(_tree_filename, 'w', 'utf-8').write(html)
    people = find_people(html)
    count = 0
    missing = []
    for email, name in people:
        if email in EXCEPTIONS:
            continue
        jpg_filename = os.path.join(dest, email + '.jpg')
        if not os.path.isfile(jpg_filename):
            url = URL.format(email=email)
            r = download(url)
            #print r.text
            assert r.status_code == 200, r.status_code
            assert r.headers['content-type'] == 'image/jpeg', r.headers['content-type']

            with open(jpg_filename, 'wb') as f:
                f.write(r.content)

            print "wrote", jpg_filename
            count += 1
            time.sleep(0.5)

            if count > 200:
                print "Break early"
                break
        size = os.stat(jpg_filename)[stat.ST_SIZE]
        if size == 3302:  # size of that anonymous pic
            if check_employee(email):
                print name.ljust(30, ' '),
                print email
                missing.append((email, name))


    report_html = open('report_template.html').read()
    names = ['<li><a href="mailto:%s">%s</a></li>' % (x[0], x[1]) for x in missing]
    report_html = report_html.replace('<ul>', '<ul>' + '\n'.join(names))
    with codecs.open('report.html', 'w', 'utf-8') as f:
        f.write(report_html)
    print "WROTE", 'report.html'
    print '; '.join([x[0] for x in missing])


def check_employee(email):
    url = MOZLDAP.format(email=email)
    r = requests.get(url)
    assert r.status_code == 200, r.status_code
    result = json.loads(r.text)
    return result

if __name__ == '__main__':
    run()

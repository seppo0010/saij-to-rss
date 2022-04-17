import base64
import json
import os

from github import Github, GithubIntegration
import requests
from feedgen.feed import FeedGenerator
import telegram

orgname, reponame = os.environ['PUBLISH_GITHUB_REPOSITORY'].split('/')

ghi = GithubIntegration(
        os.environ['PUBLISH_GITHUB_APP_ID'],
        base64.b64decode(os.environ['PUBLISH_GITHUB_PRIVATE_KEY_BASE64']),
)
g = Github(ghi.get_access_token(
    ghi.get_installation(orgname, reponame).id
).token)
repo = g.get_repo(os.environ['PUBLISH_GITHUB_REPOSITORY'])

bot = telegram.Bot(token=os.environ['PUBLISH_TELEGRAM_TOKEN'])
def send_tg(url, summary, text):
    bot.send_message(chat_id=os.environ['PUBLISH_TELEGRAM_CHAT_ID'], text=f'{url}\n\n{summary}\n\n{text}')

fg = FeedGenerator()
fg.title('SAIJ: Jurisprudencia CSJN')
fg.link(href='http://www.saij.gob.ar/')
fg.description('Tribunal: CORTE SUPREMA DE JUSTICIA DE LA NACION; Tipo de Documento: Jurisprudencia')

URL = 'http://www.saij.gob.ar/busqueda?o=0&p=25&f=Total%7CFecha%7CEstado+de+Vigencia%5B5%2C1%5D%7CTema%5B5%2C1%5D%7COrganismo%5B5%2C1%5D%7CAutor%5B5%2C1%5D%7CJurisdicci%C3%B3n%5B5%2C1%5D%7CTribunal%2FCORTE+SUPREMA+DE+JUSTICIA+DE+LA+NACION%7CPublicaci%C3%B3n%5B5%2C1%5D%7CColecci%C3%B3n+tem%C3%A1tica%5B5%2C1%5D%7CTipo+de+Documento%2FJurisprudencia&s=fecha-rango%7CDESC&v=colapsada'

sent_file = repo.get_contents("sent.json", ref="database")
sent = json.loads(sent_file.decoded_content)

r = requests.get(URL)
data = r.json()
for doc in data['searchResults']['documentResultList']:
    abstract = json.loads(doc['documentAbstract'])
    permaurl = 'http://www.saij.gob.ar/{}/{}'.format(
        abstract['document']['metadata']['friendly-url']['description'],
        abstract['document']['metadata']['uuid'],
    )

    url = 'http://www.saij.gob.ar/view-document?guid={}'.format(
        abstract['document']['metadata']['uuid'],
    )
    r = requests.get(url)
    data = json.loads(r.json()['data'])

    url = 'http://www.saij.gob.ar/busqueda?r=id-infojus%3ASU{}&o=0&p=500&f=Total'.format(
        data['document']['content']['sumarios-relacionados']['sumario-relacionado'][0],
    )
    r = requests.get(url)
    data = r.json()

    res = data['searchResults']['documentResultList']
    if len(res) == 0:
        continue
    url = 'http://www.saij.gob.ar/view-document?guid={}'.format(
        res[0]['uuid'],
    )
    r = requests.get(url)
    data = json.loads(r.json()['data'])
    fe = fg.add_entry()
    fe.id(permaurl)
    fe.link(href=permaurl)
    fe.title(data['document']['content']['sumario'])
    fe.description(data['document']['content']['texto'])

    if url not in sent:
        sent.append(url)
        send_tg(permaurl, data['document']['content']['sumario'], data['document']['content']['texto'])

repo.update_file(sent_file.path, "Update sent", json.dumps(sent), sent_file.sha, branch="database")

rss = fg.rss_str(pretty=True)
contents = repo.get_contents("rss.xml", ref="gh-pages")
repo.update_file(contents.path, "Update rss", rss, contents.sha, branch="gh-pages")

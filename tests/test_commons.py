"""Commons photos: free licences only, credits recorded, allowlisted hosts only."""
from __future__ import annotations
import json
import httpx
import pytest
import channel.commons as commons


@pytest.mark.parametrize('lic,ok',[('CC BY-SA 4.0',True),('CC BY 2.0',True),('CC0',True),('Public domain',True),
                                    ('PD-USGov',True),('CC BY-NC 2.0',False),('CC BY-ND 4.0',False),('All rights reserved',False),('',False)])
def test_license_filter(lic,ok):
    assert commons.license_allowed(lic) is ok


def _page(title,lic,width=4000,height=3000,host='upload.wikimedia.org',index=1,mime='image/jpeg'):
    return {'title':title,'index':index,'imageinfo':[{'thumburl':f'https://{host}/x/{title}.jpg','width':width,'height':height,'mime':mime,
            'descriptionurl':'https://commons.wikimedia.org/wiki/'+title,
            'extmetadata':{'LicenseShortName':{'value':lic},'Artist':{'value':'<a href="x">Ana P&eacute;rez</a>'}}}]}


def _client(pages,calls):
    def handler(req):
        calls.append(str(req.url))
        if req.url.host=='commons.wikimedia.org':
            return httpx.Response(200,json={'query':{'pages':pages}})
        return httpx.Response(200,content=b'\xff\xd8jpegdata')
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_picks_free_large_landscape_photo_and_writes_credits(tmp_path):
    pages=[_page('File:A.jpg','CC BY-NC 2.0',index=1),_page('File:B.jpg','CC BY-SA 4.0',width=800,index=2),
           _page('File:C.jpg','CC BY-SA 4.0',width=2000,height=3000,index=3),_page('File:D.jpg','CC BY 2.0',index=4)]
    sb=tmp_path/'storyboard.json'
    sb.write_text(json.dumps({'scenes':[{'index':0,'visual_type':'text_overlay','search_terms':''},
                                        {'index':1,'visual_type':'broll','search_terms':'green anaconda'},
                                        {'index':2,'visual_type':'broll','search_terms':'woman portrait'}]}))
    calls=[]
    summary=commons.fetch_for_storyboard(sb,tmp_path/'photos',client_factory=lambda:_client(pages,calls))
    assert summary=={'photos':1,'missing_scenes':[2],'missing_reasons':{'2':'no_qualifying_photo'}}
    amap=json.loads((tmp_path/'photos'/'asset_map.json').read_text())
    assert list(amap)==['1'] and amap['1'].endswith('scene_1.jpg')
    credits=json.loads((tmp_path/'photos'/'credits.json').read_text())
    assert credits[0]['title']=='File:D.jpg' and credits[0]['author']=='Ana Pérez' and credits[0]['license']=='CC BY 2.0'
    assert 'D.jpg — Ana Pérez, CC BY 2.0' in (tmp_path/'photos'/'credits.txt').read_text()
    assert sum('commons.wikimedia.org' in c for c in calls)==1  # landscape found first; blocked terms never searched


def test_same_photo_not_reused_and_foreign_hosts_refused(tmp_path):
    pages=[_page('File:D.jpg','CC0'),_page('File:E.jpg','CC0',host='evil.example',index=2)]
    sb=tmp_path/'s.json'
    sb.write_text(json.dumps({'scenes':[{'index':0,'visual_type':'broll','search_terms':'jaguar'},
                                        {'index':1,'visual_type':'broll','search_terms':'jaguar'}]}))
    calls=[]
    summary=commons.fetch_for_storyboard(sb,tmp_path/'p',client_factory=lambda:_client(pages,calls))
    assert summary=={'photos':1,'missing_scenes':[1],'missing_reasons':{'1':'no_qualifying_photo (pages=2, imageinfo=2, error=None, rejects={\'reused\': 1, \'host\': 1})'}}
    assert not any('evil.example' in c for c in calls)


def test_portrait_used_only_when_no_landscape(tmp_path):
    pages=[_page('File:P.jpg','CC0',width=2000,height=3000)]
    sb=tmp_path/'s.json'
    sb.write_text(json.dumps({'scenes':[{'index':0,'visual_type':'broll','search_terms':'jaguar'}]}))
    calls=[]
    assert commons.fetch_for_storyboard(sb,tmp_path/'p',client_factory=lambda:_client(pages,calls))=={'photos':1,'missing_scenes':[]}
    assert sum('commons.wikimedia.org' in c for c in calls)==2

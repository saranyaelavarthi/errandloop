from app.matching import find_matches


def board():
    return {'trips':[
        {'id':'ta','member':'a','status':'open','destination':'library','depart':200,'returns':300,'capacity':1},
        {'id':'tb','member':'b','status':'open','destination':'shop','depart':200,'returns':400,'capacity':1}],
        'requests':[
        {'id':'ra','member':'a','status':'open','destination':'shop','ready':250,'deadline':350,'units':2,'item':'Parcel'},
        {'id':'rb','member':'b','status':'open','destination':'library','ready':100,'deadline':500,'units':1,'item':'Book'}]}


def test_explains_each_actual_constraint_without_changing_posts():
    s=board()
    result=find_matches(s,100)
    item=next(x for x in result['unmatched'] if x['member']=='a')
    assert item['checks'][0]['blockers']==[
        'Leaves 1 min before your item is ready.',
        'Returns 1 min after your deadline.',
        'Available space: 1; your request needs 2.']
    assert not result['candidates']
    assert s['requests'][0]['units']==2
    s['requests'][0].update(ready=100,deadline=500,units=1)
    assert len(find_matches(s,100)['candidates'])==1


def test_no_self_pickup_and_no_departed_trip_suggestions():
    s=board()
    s['trips'][1]['depart']=99
    s['trips'][0]['destination']='shop'
    item=next(x for x in find_matches(s,100)['unmatched'] if x['member']=='a')
    assert item['checks']==[]
    assert 'Nobody else' in item['reason']

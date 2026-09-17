import time

PLACES = [
    {'id': 'grocery', 'name': 'Corner Store', 'type': 'Groceries', 'walk': 8, 'color': 'orange'},
    {'id': 'print', 'name': 'Print Point', 'type': 'Printing & stationery', 'walk': 6, 'color': 'purple'},
    {'id': 'library', 'name': 'Central Library', 'type': 'Reserved books', 'walk': 10, 'color': 'blue'},
    {'id': 'canteen', 'name': 'Campus Canteen', 'type': 'Prepared orders', 'walk': 5, 'color': 'green'},
]


def seed(now=None):
    now = int(now or time.time())
    members = [
        {'id': 'you', 'name': 'Sana', 'initials': 'SA', 'color': 'orange', 'room': 'Courtyard group'},
        {'id': 'asha', 'name': 'Asha', 'initials': 'AS', 'color': 'purple', 'room': 'Block A'},
        {'id': 'ravi', 'name': 'Ravi', 'initials': 'RA', 'color': 'green', 'room': 'Block B'},
        {'id': 'meena', 'name': 'Meena', 'initials': 'ME', 'color': 'blue', 'room': 'Block A'},
        {'id': 'dev', 'name': 'Dev', 'initials': 'DE', 'color': 'orange', 'room': 'Block C'},
        {'id': 'tara', 'name': 'Tara', 'initials': 'TA', 'color': 'pink', 'room': 'Block B'},
        {'id': 'kabir', 'name': 'Kabir', 'initials': 'KA', 'color': 'yellow', 'room': 'Block C'},
    ]
    trips, requests = [], []
    rows = [('you', 'grocery', 'print', 'My prepaid assignment printout', 20, 45),
            ('asha', 'print', 'library', 'My reserved design book', 25, 50),
            ('ravi', 'library', 'grocery', 'My prepaid packet of coffee', 30, 55),
            ('meena', 'canteen', 'print', 'My prepaid project binding', 40, 65),
            ('dev', 'print', 'canteen', 'My packed lunch order', 45, 70),
            ('tara', 'grocery', 'library', 'My reserved paperback', 50, 75)]
    notes = {'you': 'Quick grocery run before class. Happy to carry a small pickup.',
             'asha': 'Collecting my lab sheets. Room for a couple of envelopes.',
             'ravi': 'Returning a book. I can collect reserved books too.',
             'meena': 'Picking up lunch after class. Prepared orders only, please.',
             'dev': 'Getting my project bound. Small stationery pickups welcome.',
             'tara': 'Just a quick shop run. Nothing bulky, please.'}
    for member, going, need, item, depart, returns in rows:
        trips.append({'id': 'trip-' + member, 'member': member, 'destination': going,
                      'depart': now + depart * 60, 'returns': now + returns * 60,
                      'capacity': 2, 'status': 'open', 'note': notes[member]})
        requests.append({'id': 'need-' + member, 'member': member, 'destination': need,
                         'item': item, 'ready': now, 'deadline': now + 100 * 60,
                         'units': 1, 'status': 'open', 'note': 'Prepared and paid for. Meet at the courtyard.'})
    return {'version': 1, 'created': now, 'members': members, 'places': PLACES,
            'trips': trips, 'requests': requests, 'loops': [], 'activity': [], 'operations': []}

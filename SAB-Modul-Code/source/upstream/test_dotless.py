import build
for mono in (False,True):
 data=build.alphabet('SAB Modul',mono)
 assert data['ı']==(data['i'][0],data['i'][1][:-1]), 'Dotless i must preserve i skeleton minus dot'
print('Sans and Mono dotless i preserve the matching i skeleton: PASS')

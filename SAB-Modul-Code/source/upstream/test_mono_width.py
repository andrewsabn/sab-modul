import build
for style,(_,t) in build.WEIGHTS.items():
 data=build.alphabet('SAB Modul',True)
 for c in 'kKкКRЯЖжХXAАNнŘŇÅÄ':
  g,a,_=build.geometry(*data[c],'SAB Modul',True,t,False,c)
  assert a==620 and g.bounds[0]>=23 and g.bounds[2]<=597,(style,c,g.bounds)
print('Mono diagonal letters stay within advance with 24-unit side space: PASS')

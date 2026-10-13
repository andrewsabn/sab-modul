import build
for mono in (False,True):
 data=build.alphabet('SAB Modul',mono)
 for style,(_,t) in build.WEIGHTS.items():
  for oblique in (False,True):
   g,a,_=build.geometry(*data['ŉ'],'SAB Modul',mono,t,oblique,'ŉ')
   assert g.geom_type=='MultiPolygon' and len(g.geoms)==2,(mono,style,oblique,g.geom_type)
print('Apostrophe remains separate from n in all28 styles')

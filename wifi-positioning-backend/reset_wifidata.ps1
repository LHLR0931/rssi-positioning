# reset_wifidata.ps1（放到项目根目录，和 manage.py 同级）
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Path ".\backup" -ErrorAction SilentlyContinue | Out-Null

# 1) 备份：仅导出 api.WiFiData（同时做整库备份）
python manage.py dumpdata api.WiFiData --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e admin.LogEntry --indent 2 > ".\backup\dump_WiFiData_$ts.json"
Copy-Item ".\db_new.sqlite3" ".\backup\db_new_$ts.sqlite3" -Force

# 2) 清空该模型数据（不动用户/Token）
python manage.py shell -c "from api.models import WiFiData as M; n,_=M.objects.all().delete(); print('deleted=', n)"

# 3) 统计检查（按 data_type 分组计数）
python manage.py shell -c "from django.apps import apps; from django.db.models import Count; M=apps.get_model('api','WiFiData'); print(list(M.objects.values('data_type').annotate(n=Count('pk')).order_by('data_type')))"

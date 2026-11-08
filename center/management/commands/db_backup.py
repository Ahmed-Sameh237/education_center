import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'إنشاء نسخة احتياطية أو استعادة قاعدة البيانات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--restore',
            type=str,
            help='مسار ملف النسخة الاحتياطية المراد استعادته',
        )

    def handle(self, *args, **options):
        db_path = settings.DATABASES['default']['NAME']
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        if options['restore']:
            backup_file = options['restore']
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, db_path)
                self.stdout.write(self.style.SUCCESS(f'تم استعادة قاعدة البيانات بنجاح من {backup_file}'))
            else:
                self.stdout.write(self.style.ERROR('ملف النسخة الاحتياطية غير موجود!'))
        else:
            # إنشاء نسخة احتياطية جديدة
            backup_name = f'db_backup_{os.path.basename(db_path)}'
            backup_file = os.path.join(backup_dir, backup_name)
            shutil.copy2(db_path, backup_file)
            self.stdout.write(self.style.SUCCESS(f'تم إنشاء النسخة الاحتياطية بنجاح: {backup_file}'))
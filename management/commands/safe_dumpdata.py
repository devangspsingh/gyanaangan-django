from django.core.management.base import BaseCommand
from django.core import serializers
from django.db import connection
from django.apps import apps
import json
from datetime import datetime, date

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

class Command(BaseCommand):
    help = 'Safely dumps the database with proper encoding handling'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='dump.json', help='Output file')
        parser.add_argument('--indent', default=2, type=int, help='JSON indentation')

    def get_model_order(self):
        """Define explicit model order for dumping"""
        return [
            ('auth', 'user'),
            ('auth', 'group'),
            ('auth', 'permission'),
            ('accounts', 'profile'),  # Add your custom models after auth
            # Add other models here
        ]

    def handle(self, *args, **options):
        try:
            output_data = []
            model_order = self.get_model_order()
            
            # First dump models in specific order
            for app_label, model_name in model_order:
                try:
                    model = apps.get_model(app_label, model_name)
                    self.stdout.write(f'Dumping {app_label}.{model_name}...')
                    queryset = model.objects.all().order_by('pk')
                    if queryset.exists():
                        data = serializers.serialize('python', queryset,
                                                  use_natural_foreign_keys=True,
                                                  use_natural_primary_keys=True)
                        output_data.extend(data)
                        self.stdout.write(f'  -> Dumped {len(data)} objects')
                except Exception as e:
                    self.stdout.write(f'  -> Error dumping {app_label}.{model_name}: {str(e)}')

            # Then dump remaining models
            all_models = apps.get_models()
            for model in all_models:
                if (model._meta.app_label, model._meta.model_name) not in model_order:
                    if model._meta.app_label != 'contenttypes':
                        self.stdout.write(f'Dumping {model._meta.label}...')
                        
                        # Get all instances including related data
                        queryset = model.objects.all().order_by('pk')
                        if queryset.exists():
                            data = serializers.serialize('python', queryset,
                                                      use_natural_foreign_keys=True,
                                                      use_natural_primary_keys=True)
                            output_data.extend(data)
                            self.stdout.write(f'  -> Dumped {len(data)} objects')
                        else:
                            self.stdout.write('  -> No objects found')

            self.stdout.write(f'Total objects to dump: {len(output_data)}')
            
            # Write to file with proper encoding
            with open(options['output'], 'w', encoding='utf-8') as f:
                json.dump(output_data, f, 
                         ensure_ascii=False, 
                         indent=options['indent'],
                         cls=DateTimeEncoder)
                
            self.stdout.write(self.style.SUCCESS(
                f'Successfully dumped {len(output_data)} objects to {options["output"]}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during dump: {str(e)}'))
            raise
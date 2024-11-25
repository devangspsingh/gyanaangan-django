from django.core.management.base import BaseCommand
from django.core import serializers
from django.db import transaction, connection
from django.apps import apps
from django.db.models.fields.related import ForeignKey
import json
from datetime import datetime
from collections import defaultdict

class Command(BaseCommand):
    help = 'Safely loads data from JSON dump into PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument('input_file', help='Input JSON file path')
        parser.add_argument('--batch-size', type=int, default=100, 
                          help='Number of objects to process in each batch')

    def expand_varchar_fields(self):
        """Expand varchar fields to accommodate longer strings"""
        with connection.cursor() as cursor:
            # Get list of actual Django model tables
            django_tables = set()
            for model in apps.get_models():
                django_tables.add(model._meta.db_table)

            # Get varchar fields only for existing Django tables
            cursor.execute("""
                SELECT table_name, column_name 
                FROM information_schema.columns 
                WHERE data_type = 'character varying'
                AND table_name = ANY(%s)
            """, [list(django_tables)])

            for table, column in cursor.fetchall():
                try:
                    cursor.execute(f"""
                        ALTER TABLE "{table}" 
                        ALTER COLUMN "{column}" TYPE varchar(1024)
                    """)
                except Exception as e:
                    self.stdout.write(f'Warning: Could not alter {table}.{column}: {str(e)}')

    def get_model_dependencies(self):
        """Build dependency graph of models"""
        dependencies = defaultdict(set)
        
        # Define critical models that should load first
        critical_models = [
            'auth.user',
            'auth.group',
            'auth.permission',
        ]
        
        # Add critical models to dependency graph
        for model_label in critical_models:
            dependencies[model_label] = set()
        
        models = apps.get_models()
        for model in models:
            model_label = f"{model._meta.app_label}.{model._meta.model_name}"
            
            # Make non-critical models depend on critical ones
            if model_label not in critical_models:
                for critical in critical_models:
                    dependencies[model_label].add(critical)
            
            # Add regular field dependencies
            for field in model._meta.fields:
                if isinstance(field, ForeignKey):
                    related_model = field.remote_field.model
                    related_label = f"{related_model._meta.app_label}.{related_model._meta.model_name}"
                    dependencies[model_label].add(related_label)
        
        return dependencies

    def sort_models_by_dependencies(self, objects):
        """Sort objects based on model dependencies using Kahn's algorithm"""
        dependencies = self.get_model_dependencies()
        model_objects = defaultdict(list)
        ordered_objects = []
        
        # Group objects by model
        for obj in objects:
            model_label = f"{obj['model']}"
            model_objects[model_label].append(obj)
        
        # Calculate in-degree for each node
        in_degree = defaultdict(int)
        for model in dependencies:
            for dep in dependencies[model]:
                in_degree[dep] += 1
        
        # Find nodes with no dependencies
        queue = []
        for model in model_objects:
            if in_degree[model] == 0:
                queue.append(model)
        
        # Process queue
        while queue:
            current = queue.pop(0)
            ordered_objects.extend(model_objects.get(current, []))
            
            # Remove current node's edges
            for model, deps in dependencies.items():
                if current in deps:
                    deps.remove(current)
                    in_degree[model] -= 1
                    if in_degree[model] == 0:
                        queue.append(model)
        
        # Check for circular dependencies
        if len(ordered_objects) < len(objects):
            self.stdout.write(self.style.WARNING('Circular dependencies detected. Falling back to simple ordering.'))
            return objects
            
        return ordered_objects

    def handle(self, *args, **options):
        try:
            self.stdout.write('Expanding varchar fields...')
            with transaction.atomic():
                self.expand_varchar_fields()

            self.stdout.write('Reading input file...')
            with open(options['input_file'], 'r', encoding='utf-8') as f:
                objects = json.load(f)

            self.stdout.write('Sorting objects by dependencies...')
            objects = self.sort_models_by_dependencies(objects)
            
            total = len(objects)
            batch_size = options['batch_size']
            
            self.stdout.write(f'Found {total} objects to process')

            with transaction.atomic():
                for i in range(0, total, batch_size):
                    batch = objects[i:i + batch_size]
                    
                    # Deserialize and create objects
                    for obj in serializers.deserialize('python', batch):
                        obj.save()
                    
                    self.stdout.write(f'Processed {min(i + batch_size, total)}/{total} objects')

            self.stdout.write(self.style.SUCCESS('Successfully loaded all data'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during load: {str(e)}'))
            raise
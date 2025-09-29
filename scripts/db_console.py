#!/usr/bin/env python3
"""
Скрипт для работы с базой данных из консоли
Использование:
    python scripts/db_console.py --help
    python scripts/db_console.py list-forms
    python scripts/db_console.py list-discounts
    python scripts/db_console.py get-form 123
    python scripts/db_console.py export-forms --format csv
"""

import asyncio
import argparse
import json
import csv
from datetime import datetime
from pathlib import Path
import sys

# Добавляем корневую папку в путь для импортов
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from shared.db import SessionLocal
from db import models


async def list_forms(limit: int = 10, offset: int = 0):
    """Показать список анкет"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(models.Form)
            .order_by(models.Form.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        forms = result.scalars().all()
        
        if not forms:
            print("Анкеты не найдены")
            return
            
        print(f"Найдено анкет: {len(forms)}")
        print("-" * 80)
        
        for form in forms:
            print(f"ID: {form.id}")
            print(f"ФИО: {form.full_name}")
            print(f"Telegram: {form.tg_username}")
            print(f"Возраст: {form.age}")
            print(f"Уровень: {form.level}")
            print(f"Создано: {form.created_at}")
            print(f"В проекте: {'Да' if form.in_project else 'Нет'}")
            print("-" * 40)


async def get_form(form_id: int):
    """Получить детальную информацию об анкете"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(models.Form).where(models.Form.id == form_id)
        )
        form = result.scalar_one_or_none()
        
        if not form:
            print(f"Анкета с ID {form_id} не найдена")
            return
            
        print(f"=== АНКЕТА ID: {form.id} ===")
        print(f"📝 ФИО: {form.full_name}")
        print(f"🎂 Возраст: {form.age}")
        print(f"🌐 Часовой пояс: {form.timezone}")
        print(f"🏙️ Город: {form.city}")
        print(f"📞 Telegram: {form.tg_username}")
        print(f"📧 Альтернативный контакт: {form.alt_contact}")
        print(f"📊 Уровень: {form.level}")
        print(f"🔄 Опыт участия: {form.participated_before}")
        print(f"🎯 Приоритет: {form.priority}")
        print(f"🎓 Цели изучения: {form.goals}")
        print(f"🎨 Хобби: {form.hobbies}")
        print(f"💬 Темы: {form.topics}")
        print(f"📅 Дни: {', '.join(form.days_list())}")
        print(f"⏰ Время: {form.time_of_day}")
        print(f"⚡ Строгость расписания: {form.schedule_strictness}")
        print(f"💡 Инициатива: {form.initiative}")
        print(f"👫 Предпочтительный партнер: {form.preferred_partner_gender}")
        print(f"📋 Заметки: {form.other_notes}")
        print(f"✅ Принял правила: {'Да' if form.accepted_rules else 'Нет'}")
        print(f"✅ Принял оферту: {'Да' if form.accepted_offer else 'Нет'}")
        print(f"✅ Принял NDA: {'Да' if form.accepted_nda else 'Нет'}")
        print(f"📸 Фото оплаты: {form.repost_photo_file_id}")
        print(f"🎯 В проекте: {'Да' if form.in_project else 'Нет'}")
        print(f"📅 Создано: {form.created_at}")


async def list_discounts():
    """Показать список скидок"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(models.Discount).order_by(models.Discount.updated_at.desc())
        )
        discounts = result.scalars().all()
        
        if not discounts:
            print("Скидки не найдены")
            return
            
        print(f"Найдено скидок: {len(discounts)}")
        print("-" * 60)
        
        for discount in discounts:
            print(f"ID: {discount.id}")
            print(f"Пользователь: {discount.user_identifier}")
            print(f"Скидка: {discount.percent}%")
            print(f"Обновлено: {discount.updated_at}")
            print("-" * 30)


async def get_stats():
    """Показать статистику"""
    async with SessionLocal() as session:
        # Общее количество анкет
        total_forms = await session.scalar(select(func.count(models.Form.id)))
        
        # Анкеты в проекте
        in_project = await session.scalar(
            select(func.count(models.Form.id)).where(models.Form.in_project == True)
        )
        
        # Анкеты по уровням
        levels_result = await session.execute(
            select(models.Form.level, func.count(models.Form.id))
            .group_by(models.Form.level)
            .order_by(func.count(models.Form.id).desc())
        )
        levels = levels_result.all()
        
        # Анкеты по дням недели
        days_result = await session.execute(
            select(models.Form.days)
        )
        all_days = []
        for row in days_result:
            try:
                days_list = json.loads(row[0] or "[]")
                all_days.extend(days_list)
            except:
                pass
        
        from collections import Counter
        days_count = Counter(all_days)
        
        # Количество скидок
        total_discounts = await session.scalar(select(func.count(models.Discount.id)))
        
        print("=== СТАТИСТИКА ===")
        print(f"📊 Всего анкет: {total_forms}")
        print(f"🎯 В проекте: {in_project}")
        print(f"📈 Скидок: {total_discounts}")
        print()
        
        print("📊 Анкеты по уровням:")
        for level, count in levels:
            print(f"  {level}: {count}")
        print()
        
        print("📅 Популярные дни недели:")
        for day, count in days_count.most_common():
            print(f"  {day}: {count}")


async def export_forms(format_type: str = "csv"):
    """Экспорт анкет в файл"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(models.Form).order_by(models.Form.created_at.desc())
        )
        forms = result.scalars().all()
        
        if not forms:
            print("Анкеты не найдены для экспорта")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == "csv":
            filename = f"forms_export_{timestamp}.csv"
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'id', 'full_name', 'age', 'timezone', 'city', 'tg_username', 
                    'alt_contact', 'level', 'participated_before', 'priority', 
                    'goals', 'hobbies', 'topics', 'days', 'time_of_day', 
                    'schedule_strictness', 'initiative', 'preferred_partner_gender', 
                    'other_notes', 'accepted_rules', 'accepted_offer', 'accepted_nda', 
                    'in_project', 'created_at'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for form in forms:
                    row = {
                        'id': form.id,
                        'full_name': form.full_name,
                        'age': form.age,
                        'timezone': form.timezone,
                        'city': form.city,
                        'tg_username': form.tg_username,
                        'alt_contact': form.alt_contact,
                        'level': form.level,
                        'participated_before': form.participated_before,
                        'priority': form.priority,
                        'goals': form.goals,
                        'hobbies': form.hobbies,
                        'topics': form.topics,
                        'days': form.days,
                        'time_of_day': form.time_of_day,
                        'schedule_strictness': form.schedule_strictness,
                        'initiative': form.initiative,
                        'preferred_partner_gender': form.preferred_partner_gender,
                        'other_notes': form.other_notes,
                        'accepted_rules': form.accepted_rules,
                        'accepted_offer': form.accepted_offer,
                        'accepted_nda': form.accepted_nda,
                        'in_project': form.in_project,
                        'created_at': form.created_at
                    }
                    writer.writerow(row)
            
            print(f"✅ Экспортировано {len(forms)} анкет в файл: {filename}")
        
        elif format_type == "json":
            filename = f"forms_export_{timestamp}.json"
            data = []
            for form in forms:
                data.append({
                    'id': form.id,
                    'full_name': form.full_name,
                    'age': form.age,
                    'timezone': form.timezone,
                    'city': form.city,
                    'tg_username': form.tg_username,
                    'alt_contact': form.alt_contact,
                    'level': form.level,
                    'participated_before': form.participated_before,
                    'priority': form.priority,
                    'goals': form.goals,
                    'hobbies': form.hobbies,
                    'topics': form.topics,
                    'days': form.days_list(),
                    'time_of_day': form.time_of_day,
                    'schedule_strictness': form.schedule_strictness,
                    'initiative': form.initiative,
                    'preferred_partner_gender': form.preferred_partner_gender,
                    'other_notes': form.other_notes,
                    'accepted_rules': form.accepted_rules,
                    'accepted_offer': form.accepted_offer,
                    'accepted_nda': form.accepted_nda,
                    'in_project': form.in_project,
                    'created_at': form.created_at.isoformat()
                })
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Экспортировано {len(forms)} анкет в файл: {filename}")


async def main():
    parser = argparse.ArgumentParser(description="Работа с базой данных Talko")
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда list-forms
    list_forms_parser = subparsers.add_parser('list-forms', help='Показать список анкет')
    list_forms_parser.add_argument('--limit', type=int, default=10, help='Количество анкет (по умолчанию: 10)')
    list_forms_parser.add_argument('--offset', type=int, default=0, help='Смещение (по умолчанию: 0)')
    
    # Команда get-form
    get_form_parser = subparsers.add_parser('get-form', help='Получить детальную информацию об анкете')
    get_form_parser.add_argument('id', type=int, help='ID анкеты')
    
    # Команда list-discounts
    subparsers.add_parser('list-discounts', help='Показать список скидок')
    
    # Команда stats
    subparsers.add_parser('stats', help='Показать статистику')
    
    # Команда export-forms
    export_parser = subparsers.add_parser('export-forms', help='Экспорт анкет в файл')
    export_parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='Формат экспорта')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'list-forms':
            await list_forms(args.limit, args.offset)
        elif args.command == 'get-form':
            await get_form(args.id)
        elif args.command == 'list-discounts':
            await list_discounts()
        elif args.command == 'stats':
            await get_stats()
        elif args.command == 'export-forms':
            await export_forms(args.format)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

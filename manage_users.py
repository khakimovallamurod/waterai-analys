#!/usr/bin/env python3
"""
WaterAI - Foydalanuvchilarni SQLite DB orqali xavfsiz boshqarish vositasi (CLI).
Parollar va shaxsiy ma'lumotlar dastur manbasida (source code) saqlanmaydi.
Barcha ma'lumotlar SQLite3 (waterai.db) bazasida shifrlangan (bcrypt) holda saqlanadi.
"""

import sys
import argparse
import getpass
from database import SessionLocal
from models import User
import auth

def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("❌ Bazada hech qanday foydalanuvchi topilmadi.")
            return

        print("\n" + "=" * 70)
        print(f"{'ID':<4} | {'Telefon':<18} | {'F.I.SH':<24} | {'Rol':<7} | {'Holat'}")
        print("=" * 70)
        for u in users:
            status = "Faol" if u.is_active else "Nofaol"
            phone_disp = auth.format_phone_display(u.phone)
            print(f"{u.id:<4} | {phone_disp:<18} | {u.full_name:<24} | {u.role:<7} | {status}")
        print("=" * 70 + "\n")
    finally:
        db.close()

def create_user(phone: str, full_name: str, role: str = "user", password: str = None):
    db = SessionLocal()
    try:
        norm_phone = auth.normalize_phone(phone)
        if not norm_phone:
            print("❌ Noto'g'ri telefon raqami formati!")
            return

        existing = db.query(User).filter(User.phone == norm_phone).first()
        if existing:
            print(f"⚠️ Ushbu raqam ({norm_phone}) bilan foydalanuvchi allaqachon mavjud!")
            return

        if not password:
            password = getpass.getpass("Yangi parol kiriting: ")
            confirm = getpass.getpass("Parolni tasdiqlang: ")
            if password != confirm:
                print("❌ Parollar mos kelmadi!")
                return

        if len(password) < 6:
            print("❌ Parol kamida 6 ta belgidan iborat bo'lishi kerak!")
            return

        new_user = User(
            phone=norm_phone,
            full_name=full_name,
            hashed_password=auth.hash_password(password),
            role=role,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        print(f"✅ Yangi {role} muvaffaqiyatli yaratildi: {norm_phone} ({full_name})")
    finally:
        db.close()

def reset_password(phone: str, new_password: str = None):
    db = SessionLocal()
    try:
        norm_phone = auth.normalize_phone(phone)
        user = db.query(User).filter(User.phone == norm_phone).first()
        if not user:
            print(f"❌ '{phone}' raqamli foydalanuvchi topilmadi!")
            return

        if not new_password:
            new_password = getpass.getpass(f"'{user.full_name}' uchun yangi parol: ")
            confirm = getpass.getpass("Parolni tasdiqlang: ")
            if new_password != confirm:
                print("❌ Parollar mos kelmadi!")
                return

        if len(new_password) < 6:
            print("❌ Parol kamida 6 ta belgidan iborat bo'lishi kerak!")
            return

        user.hashed_password = auth.hash_password(new_password)
        db.commit()
        print(f"✅ Parol muvaffaqiyatli yangilandi: {norm_phone}")
    finally:
        db.close()

def change_role(phone: str, new_role: str):
    if new_role not in ["admin", "user"]:
        print("❌ Rol faqat 'admin' yoki 'user' bo'lishi mumkin!")
        return

    db = SessionLocal()
    try:
        norm_phone = auth.normalize_phone(phone)
        user = db.query(User).filter(User.phone == norm_phone).first()
        if not user:
            print(f"❌ '{phone}' raqamli foydalanuvchi topilmadi!")
            return

        user.role = new_role
        db.commit()
        print(f"✅ Foydalanuvchi roli o'zgartirildi: {norm_phone} -> {new_role}")
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="WaterAI SQLite3 Foydalanuvchilar Boshqaruvi")
    subparsers = parser.add_subparsers(dest="command", help="Buyruqlar")

    # list
    subparsers.add_parser("list", help="Barcha foydalanuvchilarni ko'rish")

    # create-admin
    admin_parser = subparsers.add_parser("create-admin", help="Yangi administrator yaratish")
    admin_parser.add_argument("--phone", required=True, help="Telefon raqami (masalan: +998901234567)")
    admin_parser.add_argument("--name", default="Bosh Administrator", help="F.I.SH")
    admin_parser.add_argument("--password", default=None, help="Parol (kiritilmasa xavfsiz so'raladi)")

    # create-user
    user_parser = subparsers.add_parser("create-user", help="Yangi foydalanuvchi yaratish")
    user_parser.add_argument("--phone", required=True, help="Telefon raqami")
    user_parser.add_argument("--name", required=True, help="F.I.SH")
    user_parser.add_argument("--password", default=None, help="Parol (kiritilmasa xavfsiz so'raladi)")

    # reset-password
    reset_parser = subparsers.add_parser("reset-password", help="Foydalanuvchi parolini yangilash")
    reset_parser.add_argument("--phone", required=True, help="Telefon raqami")
    reset_parser.add_argument("--password", default=None, help="Yangi parol")

    # change-role
    role_parser = subparsers.add_parser("change-role", help="Foydalanuvchi rolini o'zgartirish")
    role_parser.add_argument("--phone", required=True, help="Telefon raqami")
    role_parser.add_argument("--role", required=True, choices=["admin", "user"], help="Yangi rol")

    args = parser.parse_args()

    if args.command == "list":
        list_users()
    elif args.command == "create-admin":
        create_user(args.phone, args.name, role="admin", password=args.password)
    elif args.command == "create-user":
        create_user(args.phone, args.name, role="user", password=args.password)
    elif args.command == "reset-password":
        reset_password(args.phone, args.password)
    elif args.command == "change-role":
        change_role(args.phone, args.role)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

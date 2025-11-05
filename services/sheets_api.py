# services/sheets_api.py

import gspread
from config import GSPREAD_JSON_STRING, SHEET_URL
from datetime import datetime
import json  # <- НОВЫЙ ИМПОРТ: для работы с JSON-строкой
import logging

class SheetsManager:
    """Менеджер для взаимодействия с Google Таблицей."""
    
    def __init__(self):
        try:
            # Преобразование JSON-строки из config.py в словарь Python
            if not GSPREAD_JSON_STRING:
                raise ValueError("Переменная GSPREAD_JSON_STRING не задана.")
                
            creds_json = json.loads(GSPREAD_JSON_STRING)
            
            # Инициализация клиента gspread напрямую из словаря
            self.client = gspread.service_account_from_dict(creds_json)
            
            # Открытие первой вкладки по URL
            self.sheet = self.client.open_by_url(SHEET_URL).sheet1 
            
        except Exception as e:
            logging.error(f"Ошибка инициализации SheetsManager: {e}")
            # Критическая ошибка, останавливаем процесс, чтобы вы увидели ошибку в логах Render
            raise Exception("Не удалось подключиться к Google Sheets. Проверьте GSPREAD_JSON_STRING и SHEET_URL.")
            
        # Проверка и установка заголовков при успешном подключении
        self._ensure_headers()


    def _ensure_headers(self):
        """Проверка наличия заголовков в таблице."""
        expected_headers = [
            'Дата/Время', 'user_id', '@username', 'Метод оплаты', 
            'ID Файла Чека', 'Статус', 'Дата начала доступа', 'Дата окончания доступа'
        ]
        try:
            current_headers = self.sheet.row_values(1)
            if current_headers != expected_headers:
                self.sheet.update('A1:H1', [expected_headers])
                logging.info("Заголовки Google Sheets обновлены.")
        except Exception as e:
            logging.error(f"Ошибка при проверке заголовков GSheets: {e}")


    def log_payment_check(self, user_id, username, method, file_id):
        """Сохраняет данные о новом чеке в Google Sheets и возвращает номер строки."""
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            user_id,
            username or 'N/A',
            method,
            file_id,
            'На проверке',
            '', # Дата начала
            ''  # Дата окончания
        ]
        self.sheet.append_row(row)
        # Получаем номер строки для последующего обновления статуса админом
        return len(self.sheet.get_all_values())

    def update_check_status(self, row_index, status, start_date=None, end_date=None):
        """Обновляет статус чека (Подтверждено/Отклонено) и даты доступа в GSheets."""
        
        # Столбец F - Статус; Столбец G - Дата начала; Столбец H - Дата окончания
        if status == '✅ Подтверждено' and start_date and end_date:
            updates = [
                (f'F{row_index}', status),
                (f'G{row_index}', start_date.strftime('%Y-%m-%d')),
                (f'H{row_index}', end_date.strftime('%Y-%m-%d'))
            ]
        else: # Для "Отклонено" или других статусов
            updates = [(f'F{row_index}', status)]
            
        self.sheet.batch_update(updates)
        return True

  feat: add SheetsManager for GSheets integration

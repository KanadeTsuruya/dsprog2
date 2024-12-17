import requests
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import sqlite3
import re


class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("天気予報アプリ")
        self.root.geometry("900x600")
        
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        self.weather_icons = {
            '晴': '☀️',
            'くもり': '☁️',
            '曇': '☁️',
            '雨': '🌧️',
            '霧': '🌁',
            '雪': '⛄️',
        }
        
        self.setup_database()
        self.area_list = self.get_area_list()
        self.create_ui()
        
        self.root.bind('<Configure>', self.on_window_resize)

    def setup_database(self):
        """データベースとテーブルの初期設定"""
        try:
            with sqlite3.connect('weather.db') as conn:
                cursor = conn.cursor()
                
                # areasテーブルの作成
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS areas (
                        area_code TEXT PRIMARY KEY,
                        area_name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT (DATETIME('now', 'localtime'))
                    )
                ''')
                
                # weather_forecastsテーブルの作成
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS weather_forecasts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        area_code TEXT,
                        forecast_date DATE NOT NULL,
                        weather_description TEXT,    -- 天気の説明
                        temperature_max INTEGER,     -- 最高気温
                        temperature_min INTEGER,     -- 最低気温
                        precipitation_probability INTEGER,  -- 降水確率
                        created_at TIMESTAMP DEFAULT (DATETIME('now', 'localtime')),
                        FOREIGN KEY (area_code) REFERENCES areas(area_code),
                        UNIQUE(area_code, forecast_date)
                    )
                ''')
                
                # インデックスの作成
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_area_date 
                    ON weather_forecasts(area_code, forecast_date)
                ''')
                
                conn.commit()
        except sqlite3.Error as e:
            print(f"データベース設定エラー: {e}")
            messagebox.showerror("エラー", "データベースの初期化中にエラーが発生しました")

    def validate_date(self, date_str):
        """日付形式の検証（YYYY-MM-DD）"""
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def create_ui(self):
        self.main_container = tk.Frame(self.root)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # コントロールフレーム
        control_frame = tk.Frame(self.main_container)
        control_frame.grid(row=0, column=0, pady=10)
        
        # 地域選択
        area_frame = tk.Frame(control_frame)
        area_frame.pack(pady=5)
        tk.Label(area_frame, text="地域を選択", font=('Helvetica', 16, 'bold')).pack(side=tk.LEFT, padx=5)
        
        self.area_combo = ttk.Combobox(
            area_frame,
            values=[area['name'] for area in self.area_list],
            width=30,
            state="readonly",
            font=('Helvetica', 14)
        )
        self.area_combo.pack(side=tk.LEFT, padx=5)
        
        # 日付選択
        date_frame = tk.Frame(control_frame)
        date_frame.pack(pady=5)
        tk.Label(date_frame, text="日付を選択 (YYYY-MM-DD)", font=('Helvetica', 12)).pack(side=tk.LEFT, padx=5)
        
        self.date_entry = tk.Entry(date_frame, font=('Helvetica', 12), width=15)
        self.date_entry.pack(side=tk.LEFT, padx=5)
        self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        # 検索ボタン
        search_button = tk.Button(
            date_frame, 
            text="検索",
            command=self.search_forecast,
            font=('Helvetica', 12)
        )
        search_button.pack(side=tk.LEFT, padx=5)
        
        # 予報表示フレーム
        self.forecast_frame = tk.Frame(self.main_container)
        self.forecast_frame.grid(row=1, column=0, sticky="nsew")
        self.forecast_frame.grid_columnconfigure(0, weight=1)
        self.forecast_frame.grid_columnconfigure(1, weight=1)
        self.forecast_frame.grid_columnconfigure(2, weight=1)
        self.forecast_frame.grid_rowconfigure(0, weight=1)
        
        # イベントバインド
        self.area_combo.bind('<<ComboboxSelected>>', self.get_weather_forecast)

    def on_window_resize(self, event):
        if hasattr(self, 'day_frames'):
            window_width = self.root.winfo_width()
            frame_width = max(200, int(window_width * 0.25))
            for frame in self.day_frames:
                frame.configure(width=frame_width)

    def get_area_list(self):
        try:
            url = "https://www.jma.go.jp/bosai/common/const/area.json"
            response = requests.get(url)
            areas = response.json()
            
            area_list = []
            if 'offices' in areas:
                with sqlite3.connect('weather.db') as conn:
                    cursor = conn.cursor()
                    
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    for office_code, office_info in areas['offices'].items():
                        if isinstance(office_info, dict) and 'name' in office_info:
                            cursor.execute('''
                                INSERT OR REPLACE INTO areas 
                                (area_code, area_name, created_at)
                                VALUES (?, ?, ?)
                            ''', (office_code, office_info['name'], current_time))
                            
                            area_list.append({
                                'code': office_code,
                                'name': office_info['name']
                            })
                    
                    conn.commit()
            
            return sorted(area_list, key=lambda x: x['name'])
        except Exception as e:
            print(f"地域リスト取得エラー: {e}")
            
            # DBから既存のデータを取得
            try:
                with sqlite3.connect('weather.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT area_code, area_name FROM areas')
                    rows = cursor.fetchall()
                    return sorted([{'code': row[0], 'name': row[1]} for row in rows],
                                key=lambda x: x['name'])
            except Exception as db_error:
                print(f"DB取得エラー: {db_error}")
                return []

    def search_forecast(self):
        """日付を指定して予報を検索"""
        date_str = self.date_entry.get().strip()
        
        if not self.validate_date(date_str):
            messagebox.showerror("エラー", "正しい日付形式で入力してください (YYYY-MM-DD)")
            return
        
        if not self.area_combo.get():
            messagebox.showerror("エラー", "地域を選択してください")
            return
        
        selected_area = next(
            (area for area in self.area_list if area['name'] == self.area_combo.get()),
            None
        )
        
        if not selected_area:
            return
        
        try:
            forecast_data = self.get_forecast_from_db(selected_area['code'], date_str)
            if forecast_data:
                self.display_forecast(forecast_data)
            else:
                messagebox.showinfo("情報", "指定された日付の予報データが見つかりませんでした")
        except Exception as e:
            print(f"予報検索エラー: {e}")
            messagebox.showerror("エラー", "予報の検索中にエラーが発生しました")

    def save_forecast_to_db(self, area_code, forecast_data):
        """天気予報データをDBに保存"""
        try:
            with sqlite3.connect('weather.db') as conn:
                cursor = conn.cursor()
                
                report = forecast_data[0]
                if 'timeSeries' not in report:
                    return
                
                for i in range(3):
                    date = datetime.now() + timedelta(days=i)
                    date_str = date.strftime("%Y-%m-%d")
                    
                    weather = "不明"
                    temp_max = 0
                    temp_min = 0
                    pop = 0
                    
                    # 天気取得
                    areas = report['timeSeries'][0].get('areas', [])
                    if areas and len(areas) > 0:
                        area = areas[0]
                        if 'weathers' in area and len(area['weathers']) > i:
                            weather = area['weathers'][i]
                    
                    # 降水確率取得
                    if len(report['timeSeries']) > 1:
                        pop_areas = report['timeSeries'][1].get('areas', [])
                        if pop_areas and len(pop_areas) > 0:
                            pop_area = pop_areas[0]
                            if 'pops' in pop_area and len(pop_area['pops']) > i:
                                pop = int(pop_area['pops'][i]) if pop_area['pops'][i] != '--' else 0
                    
                    # 気温取得
                    if len(report['timeSeries']) > 2:
                        temp_areas = report['timeSeries'][2].get('areas', [])
                        if temp_areas and len(temp_areas) > 0:
                            temp_area = temp_areas[0]
                            if 'temps' in temp_area and len(temp_area['temps']) > i*2:
                                temp_max = int(temp_area['temps'][i*2]) if temp_area['temps'][i*2] != '--' else 0
                                if len(temp_area['temps']) > i*2+1:
                                    temp_min = int(temp_area['temps'][i*2+1]) if temp_area['temps'][i*2+1] != '--' else 0
                    
                    # 既存のデータを更新または挿入
                    cursor.execute('''
                        INSERT OR REPLACE INTO weather_forecasts 
                        (area_code, forecast_date, weather_description, 
                        temperature_max, temperature_min, precipitation_probability)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (area_code, date_str, weather, temp_max, temp_min, pop))
                
                conn.commit()
        except Exception as e:
            print(f"予報保存エラー: {e}")

    def get_forecast_from_db(self, area_code, date_str=None):
        try:
            with sqlite3.connect('weather.db') as conn:
                cursor = conn.cursor()
                if date_str:
                    cursor.execute('''
                        SELECT forecast_date, weather_description, 
                            temperature_max, temperature_min, precipitation_probability
                        FROM weather_forecasts
                        WHERE area_code = ? AND forecast_date = ?
                        ORDER BY forecast_date
                    ''', (area_code, date_str))
                else:
                    cursor.execute('''
                        SELECT forecast_date, weather_description, 
                            temperature_max, temperature_min, precipitation_probability
                        FROM weather_forecasts
                        WHERE area_code = ? AND forecast_date >= date('now')
                        ORDER BY forecast_date
                        LIMIT 3
                    ''', (area_code,))
                return cursor.fetchall()
        except Exception as e:
            print(f"予報取得エラー: {e}")
            return []

    def get_weather_forecast(self, event):
        selected_area_name = self.area_combo.get()
        selected_area = next(
            (area for area in self.area_list if area['name'] == selected_area_name),
            None
        )
        
        if not selected_area:
            return

        try:
            # APIから最新の天気予報を取得してDBに保存
            url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{selected_area['code']}.json"
            response = requests.get(url)
            forecast_data = response.json()
            self.save_forecast_to_db(selected_area['code'], forecast_data)
            
            # DBから予報を取得して表示
            forecast_data = self.get_forecast_from_db(selected_area['code'])
            if forecast_data:
                self.display_forecast(forecast_data)
        except Exception as e:
            print(f"天気予報取得エラー: {e}")
            # APIエラー時はDBからの取得を試みる
            forecast_data = self.get_forecast_from_db(selected_area['code'])
            if forecast_data:
                self.display_forecast(forecast_data)

    def display_forecast(self, forecast_data):
        """天気予報の表示（DBのデータを使用）"""
        for widget in self.forecast_frame.winfo_children():
            widget.destroy()

        self.day_frames = []
        window_width = self.root.winfo_width()
        frame_width = max(200, int(window_width * 0.25))

        for i, forecast in enumerate(forecast_data):
            date_str, weather, temp_max, temp_min, pop = forecast

            day_frame = tk.Frame(
                self.forecast_frame,
                relief=tk.RAISED,
                borderwidth=2,
                width=frame_width,
                height=400
            )
            day_frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            day_frame.grid_propagate(False)
            self.day_frames.append(day_frame)

            tk.Label(day_frame, text=date_str, font=('Helvetica', 16, 'bold')).pack(pady=5)

            # 天気情報アイコンと説明表示
            icons = self.get_weather_icons(weather)
            icon_label = tk.Label(day_frame, text=icons, font=('Helvetica', 30))
            icon_label.pack(pady=10)

            # 天気説明文
            weather_label = tk.Label(day_frame, text=weather, wraplength=250, font=('Helvetica', 12))
            weather_label.pack(pady=5)

            # 気温情報
            temp_frame = tk.Frame(day_frame)
            temp_frame.pack(pady=5)
            tk.Label(temp_frame, text="気温：", font=('Helvetica', 12)).pack(side=tk.LEFT)
            tk.Label(temp_frame, text=f"最高 {temp_max}℃", font=('Helvetica', 12)).pack(side=tk.LEFT)
            tk.Label(temp_frame, text=" / ", font=('Helvetica', 12)).pack(side=tk.LEFT)
            tk.Label(temp_frame, text=f"最低 {temp_min}℃", font=('Helvetica', 12)).pack(side=tk.LEFT)

            # 降水確率
            pop_frame = tk.Frame(day_frame)
            pop_frame.pack(pady=5)
            tk.Label(pop_frame, text=f"降水確率：{pop}%", font=('Helvetica', 12)).pack()

    def get_weather_icons(self, weather_str):
        icons = []
        for key, icon in self.weather_icons.items():
            if key in weather_str:
                icons.append(icon)
        if len(icons) > 3:
            return " ".join(icons[:3]) + " ..."
        return " ".join(icons) if icons else '❓'


def main():
    root = tk.Tk()
    app = WeatherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
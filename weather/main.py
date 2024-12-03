import requests
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta


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
        
        self.area_list = self.get_area_list()
        self.create_ui()
        
        self.root.bind('<Configure>', self.on_window_resize)

    def get_area_list(self):
        try:
            url = "https://www.jma.go.jp/bosai/common/const/area.json"
            response = requests.get(url)
            areas = response.json()
            
            area_list = []
            if 'offices' in areas:
                for office_code, office_info in areas['offices'].items():
                    if isinstance(office_info, dict) and 'name' in office_info:
                        area_list.append({
                            'code': office_code,
                            'name': office_info['name']
                        })
            
            return sorted(area_list, key=lambda x: x['name'])
        except Exception as e:
            print(f"地域リスト取得エラー: {e}")
            return []

    def create_ui(self):
        self.main_container = tk.Frame(self.root)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        control_frame = tk.Frame(self.main_container)
        control_frame.grid(row=0, column=0, pady=10)
        
        tk.Label(control_frame, text="地域を選択", font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        self.area_combo = ttk.Combobox(
            control_frame,
            values=[area['name'] for area in self.area_list],
            width=30,
            state="readonly",
            font=('Helvetica', 14)
        )
        self.area_combo.pack(pady=10)
        self.area_combo.bind('<<ComboboxSelected>>', self.get_weather_forecast)

        self.forecast_frame = tk.Frame(self.main_container)
        self.forecast_frame.grid(row=1, column=0, sticky="nsew")
        self.forecast_frame.grid_columnconfigure(0, weight=1)
        self.forecast_frame.grid_columnconfigure(1, weight=1)
        self.forecast_frame.grid_columnconfigure(2, weight=1)
        self.forecast_frame.grid_rowconfigure(0, weight=1)

    def on_window_resize(self, event):
        if hasattr(self, 'day_frames'):
            window_width = self.root.winfo_width()
            frame_width = max(200, int(window_width * 0.25))
            for frame in self.day_frames:
                frame.configure(width=frame_width)

    def get_weather_forecast(self, event):
        selected_area_name = self.area_combo.get()
        selected_area = next(
            (area for area in self.area_list if area['name'] == selected_area_name), 
            None
        )
        
        if not selected_area:
            return

        try:
            url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{selected_area['code']}.json"
            response = requests.get(url)
            forecast_data = response.json()
            self.display_forecast(forecast_data)
        except Exception as e:
            print(f"天気予報取得エラー: {e}")

    def display_forecast(self, forecast_data):
        for widget in self.forecast_frame.winfo_children():
            widget.destroy()

        self.day_frames = []
        window_width = self.root.winfo_width()
        frame_width = max(200, int(window_width * 0.25))

        for i in range(3):
            date = datetime.now() + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")

            day_frame = tk.Frame(
                self.forecast_frame,
                relief=tk.RAISED,
                borderwidth=2,
                width=frame_width,
                height=400  # 高さを増やして新しい情報を表示できるようにする
            )
            day_frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            day_frame.grid_propagate(False)
            self.day_frames.append(day_frame)

            tk.Label(day_frame, text=date_str, font=('Helvetica', 16, 'bold')).pack(pady=5)

            # 予報データ取得
            report = forecast_data[0]
            weather = "不明"
            temp_max = "--"
            temp_min = "--"
            pop = "--"
            
            if 'timeSeries' in report:
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
                            pop = pop_area['pops'][i]

                # 気温取得
                if len(report['timeSeries']) > 2:
                    temp_areas = report['timeSeries'][2].get('areas', [])
                    if temp_areas and len(temp_areas) > 0:
                        temp_area = temp_areas[0]
                        if 'temps' in temp_area and len(temp_area['temps']) > i*2:
                            temp_max = temp_area['temps'][i*2]
                            if len(temp_area['temps']) > i*2+1:
                                temp_min = temp_area['temps'][i*2+1]

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
from datetime import datetime,timedelta
import json
import os
import math

FILE_NAME = "stats.json"

def get_iso_week_of_month(dt):
    # 1. 해당 날짜가 속한 주의 목요일을 찾음 (ISO 표준의 핵심 기준일)
    # dt.weekday() -> 월(0), 화(1), 수(2), 목(3), 금(4), 토(5), 일(6)
    # 현재 날짜에서 (요일 - 3)을 빼면 무조건 그 주의 목요일이 나옴
    target_thursday = dt - timedelta(days=(dt.weekday() - 3))
    
    # 2. 그 목요일이 속한 실제 연도와 월을 기준달로 설정
    base_year = target_thursday.year
    base_month = target_thursday.month
    
    # 3. 해당 기준달의 첫 번째 날 구하기
    first_day_of_month = target_thursday.replace(day=1)
    
    # 4. 해당 기준달의 첫 번째 목요일 구하기
    # (첫날 요일에서 목요일(3)까지의 거리를 계산해서 더함)
    first_thursday = first_day_of_month + timedelta(days=(3 - first_day_of_month.weekday() + 7) % 7)
    
    # 5. 주차 계산: (현재 목요일 - 첫 번째 목요일) // 7 + 1
    week_number = (target_thursday - first_thursday).days // 7 + 1
    
    # [년, 월, 주차] int 배열 반환
    return [base_year, base_month, week_number]

class memb:
    def __init__(self,_name,_id):
        self.name=_name
        self.userid=_id
        self.time=timedelta(0)
        self._ing=False
        self.timestamp=datetime.now()
        self.time_week=timedelta(0)
        self.time_month=timedelta(0)
        
    def update_in(self): #입장
        if self._ing == False:
            self._ing=True
            self.timestamp=datetime.now()

    def update_out(self): #퇴장
        self._ing=False
        time_adder = datetime.now() -self.timestamp
        self.time += time_adder
        self.time_week += time_adder
        self.time_month += time_adder
    
    def update(self):
        if self._ing:
            self.update_out()
            self.update_in()

    def printing(self): # "접속 시간 : 닉네임(id)" 리턴
        rttime = (str(self.time).split('.')[0])
        return f"{rttime} : {self.name}({self.userid})\n"     

    def reset(self):
        self.time=timedelta(0)

class membermanager:
    def __init__(self): # 딱 한 번만 사용
        self.members={}
        self.timestamp=datetime.now()
        self.timestamp_recently=datetime.now()
        self.stats = self.load_stats()
    
    def load_stats(self):
        if os.path.exists(FILE_NAME):
            with open(FILE_NAME, "r", encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_stats(self):
        with open(FILE_NAME, "w", encoding='utf-8') as f:
            json.dump(self.stats, f, indent=4, ensure_ascii=False)


    def update(self):
        self.timestamp_recently=datetime.now()
        for _id in self.members:
            self.members[_id].update()
        self.save_in_progress_data()  # stats 업데이트
        self.save_stats()  # JSON 저장

    def add(self,mem): 
        self.members[mem.userid]=mem        

    def enterexit(self,_name,_id,inout): #입장 및 퇴장 시
        if _id in self.members:
            if self.members[_id].name != _name:#닉네임 변경 체크
                self.members[_id].name = _name

            if(inout=='in'):
                self.members[_id].update_in()
            if(inout=='out'):
                self.members[_id].update_out()

        elif(inout=='in'):
            self.add(memb(_name, _id))
            self.members[_id].update_in() 

    def printing(self):
        self.members={k: v for k, v in sorted(self.members.items(), key=lambda item: item[1].time, reverse=True)} # 시간 기준 내림차순 정렬

        rt=(str(self.timestamp).split('.')[0])
        rt+='부터 시작된 기록입니다.\n'
        rt+=''.join([mem.printing() for mem in self.members.values()])
        return rt
    
    def printing_week(self):
        # 1. 날짜 및 주차 계산
        base = datetime.now() - timedelta(days=1)
        start_str = (base - timedelta(days=6)).strftime('%Y-%m-%d')
        end_str = base.strftime('%Y-%m-%d')
        y, m, w = get_iso_week_of_month(base)
        
        year_key, month_key, week_key = f"{y}년", f"{m}월", f"{w}주차"
        
        # 2. 데이터 구조 확보
        year_data = self.stats.setdefault(year_key, {})
        month_data = year_data.setdefault(month_key, {"total": {}})
        week_data = month_data.setdefault(week_key, {})

        # 3. 데이터 저장 및 멤버 기록 초기화
        for _id in list(self.members):
            time_week = self.members[_id].time_week
            if time_week > timedelta(0):
                if _id not in week_data:
                    # 저장할 때 'time'을 int(초)로 초기화
                    week_data[_id] = {"time": 0, "nickname": self.members[_id].name}
                
                # timedelta를 초 단위 정수로 변환하여 합산
                week_data[_id]["time"] += int(time_week.total_seconds())
                
                # 주간 기록 초기화
                self.members[_id].time_week = timedelta(0)

        # 4. 정렬 후 덮어쓰기
        # 이제 x[1]["time"]은 정수(초)이므로 그대로 비교 가능
        sorted_week_dict = dict(sorted(
            week_data.items(), 
            key=lambda x: x[1]["time"], 
            reverse=True
        ))
        month_data[week_key] = sorted_week_dict
        
        # 5. 출력용 문자열 생성
        rt = f"{year_key} {month_key} {week_key} 결산 ({start_str} ~ {end_str})\n"
        rt += "------------------------------------------\n"
        
        body = []
        for _id, data in month_data[week_key].items():
            time_str = str(timedelta(seconds=int(data["time"])))
            body.append(f"{time_str} : {data['nickname']}({_id})")

        rt += "\n".join(body) if body else "이번 주 기록된 활동이 없습니다."
        rt += "\n------------------------------------------"

        if "_in_progress" in self.stats:
            for _id in self.stats["_in_progress"]:
                self.stats["_in_progress"][_id]["time_week"] = 0

        self.save_stats()
        return rt

    def printing_month(self):
        # 1. 날짜 설정 (어제 기준)
        base = datetime.now() - timedelta(days=1)
        year_key = f"{base.year}년"
        month_key = f"{base.month}월"
        
        start_str = base.replace(day=1).strftime('%Y-%m-%d')
        end_str = base.strftime('%Y-%m-%d')

        # 2. 데이터 구조 확보 (stats[년][월]["total"] 경로)
        year_data = self.stats.setdefault(year_key, {})
        month_data = year_data.setdefault(month_key, {"total": {}})
        total_data = month_data["total"] # 월간 합산 데이터 저장소

        # 3. 멤버별 월간 기록(time_month) 정산 및 초기화
        for _id in list(self.members):
            m_time = self.members[_id].time_month
            
            if m_time > timedelta(0):
                if _id not in total_data:
                    total_data[_id] = {"time": 0, "nickname": self.members[_id].name}
                
                # 초(int) 단위로 변환하여 누적 저장
                total_data[_id]["time"] += int(m_time.total_seconds())
                
                # 월간 기록 초기화 (주간 기록과는 별도로 초기화)
                self.members[_id].time_month = timedelta(0)

        # 4. total_data 자체를 시간순 정렬하여 덮어쓰기
        sorted_total = dict(sorted(
            total_data.items(),
            key=lambda x: x[1]["time"],
            reverse=True
        ))
        month_data["total"] = sorted_total

        # 5. 출력용 문자열 생성
        rt = f" {year_key} {month_key} 월간 결산 ({start_str} ~ {end_str})\n"
        rt += "==========================================\n"
        
        body = []
        for _id, data in month_data["total"].items():
            time_str = str(timedelta(seconds=int(data["time"])))
            body.append(f"{time_str} : {data['nickname']}({_id})")

        if not body:
            rt += "이번 달 기록된 활동이 없습니다."
        else:
            rt += "\n".join(body)
        
        rt += "\n=========================================="

        if "_in_progress" in self.stats:
            for _id in self.stats["_in_progress"]:
                self.stats["_in_progress"][_id]["time_month"] = 0
                
        self.save_stats()
        return rt
    


    def reset(self): # /reset 입력 시, update 후 printing 출력 후 동작
        self.timestamp=datetime.now()
        self.timestamp_recently=datetime.now()

        for _id in list(self.members):
            if self.members[_id]._ing:
                self.members[_id].reset()
            else:
                del self.members[_id]

    def save_in_progress_data(self):
        """정산 전 진행 중인 time_week, time_month를 stats에 추가"""
        self.stats["_in_progress"] = {}
        for _id, member in self.members.items():
            if member.time_week > timedelta(0) or member.time_month > timedelta(0):
                self.stats["_in_progress"][_id] = {
                    "name": member.name,
                    "time_week": int(member.time_week.total_seconds()),
                    "time_month": int(member.time_month.total_seconds())
                }

    def load_in_progress_data(self):
            if "_in_progress" in self.stats:
                for _id, data in self.stats["_in_progress"].items():
                    if _id not in self.members:
                        self.members[_id] = memb(data["name"], _id)
                    
                    self.members[_id].time_week = timedelta(seconds=data["time_week"])
                    self.members[_id].time_month = timedelta(seconds=data["time_month"])
                del self.stats["_in_progress"]

# kernel.py
import datetime
import psutil
import time

class ParsKernel:
    _instance = None

    # استفاده از الگوی Singleton (تک‌نمونه‌ای) تا فقط یک کرنل در سیستم وجود داشته باشد
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ParsKernel, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # این شرط برای جلوگیری از مقداردهی مجدد در فراخوانی‌های بعدی است
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.start_time = time.time()
        self.process_list = {}  # دیکشنری برای نگهداری فرآیندهای شبیه‌سازی شده
        self.kernel_version = "0.1.0"
        print(f"PRSKernel v{self.kernel_version} initialized.")
        
        # صف رویداد برای ارتباط با UI (در آینده می‌توان از این استفاده کرد)
        # self.event_queue = [] 

    def update(self):
        """
        این متد در هر فریم از حلقه اصلی بازی فراخوانی می‌شود.
        می‌تواند وظایف پس‌زمینه کرنل را انجام دهد.
        """
        # در حال حاضر کار خاصی انجام نمی‌دهد، اما چارچوب آن آماده است.
        pass

    def register_process(self, app_id, app_name):
        """یک برنامه (فرآیند) جدید را در لیست فرآیندها ثبت می‌کند."""
        if app_id in self.process_list:
            print(f"Kernel: Process {app_id} is already running.")
            return False
            
        pid = len(self.process_list) + 1000 # یک شناسه فرآیند شبیه‌سازی شده
        self.process_list[app_id] = {
            'pid': pid,
            'name': app_name,
            'start_time': time.time(),
        }
        print(f"Kernel: Registered process '{app_name}' (PID: {pid})")
        return True

    def terminate_process(self, app_id):
        """یک فرآیند را از لیست حذف می‌کند."""
        if app_id not in self.process_list:
            print(f"Kernel: Process {app_id} not found for termination.")
            return False
            
        proc_info = self.process_list.pop(app_id)
        print(f"Kernel: Terminated process '{proc_info['name']}' (PID: {proc_info['pid']})")
        return True

    def get_process_list(self):
        """لیست فرآیندهای در حال اجرا را برمی‌گرداند."""
        return list(self.process_list.values())

    def syscall(self, call_type, **kwargs):
        """
        یک رابط شبیه‌سازی شده برای فراخوانی‌های سیستمی (Syscall).
        برنامه‌ها می‌توانند از این طریق از کرنل درخواست‌هایی داشته باشند.
        """
        if call_type == 'GET_SYS_INFO':
            # اطلاعات واقعی سیستم را با psutil برمی‌گرداند
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'uptime_seconds': time.time() - self.start_time
            }
            
        elif call_type == 'GET_TIME':
            return datetime.datetime.now()
            
        elif call_type == 'GET_KERNEL_VERSION':
            return self.kernel_version

        # (مثال برای آینده)
        # elif call_type == 'SEND_NOTIFICATION':
        #     self.event_queue.append({'type': 'notification', 'data': kwargs})
        #     return {'status': 'success'}

        else:
            print(f"Kernel: Unknown syscall '{call_type}'")
            return None

# یک نمونه واحد از کرنل ایجاد می‌کنیم تا در کل برنامه قابل دسترسی باشد
kernel_instance = ParsKernel()

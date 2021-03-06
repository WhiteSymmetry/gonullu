import random
import shutil

from docker import Client
import psutil
from gonullu.log import Log


class Docker:
    def __init__(self, parameters=None):
        self.log = Log()
        self.name = None
        self.memory_limit = self.set_memory_limit(parameters.memory_limit)
        self.binds = {}
        self.volumes = []
        self.package_name = None
        self.image = None
        self.cpu_set = self.set_cpu_set(parameters.cpu_set)
        self.command = None
        self.my_client = None
        self.host_config = None
        self.my_container = None

    def start(self):
        # containerımızı parametreleri ile çalıştıracağımız fonksiyonumuz.
        if not self.my_client:
            # my_client'de çalışan docker process'ini yakalıyorum.
            self.my_client = Client(base_url='unix://var/run/docker.sock')

        # container'ımızın host configlerini yapalım.
        self.host_config = self.my_client.create_host_config(mem_limit='%sM' % self.memory_limit, binds=self.binds)
        # hadi şimdi aynı isimle bir containerımız var mı görelim.
        self.control_docker()
        # kullanılacak imaj son sürüme yükseltelim
        self.my_client.pull(self.image)
        # my_container ile konteynırımızı oluşturuyoruz ve onda saklıyoruz.
        self.my_container = self.my_client.create_container(image=self.image, command=self.command, name=self.name,
                                                            volumes=self.volumes,
                                                            host_config=self.host_config)
        # ve konteynırımızı çalıştırmaya başlıyoruz.
        self.my_client.start(self.name)

    def pause(self):
        # containerımızı durdurmak için çalıştıracağımız fonksiyonumuz.
        self.my_client.pause(self.name)

    def resume(self):
        # containerımızı devam ettirmek için çalıştıracağımız fonksiyonumuz.
        self.my_client.unpause(self.name)

    def stop(self):
        # konteynırımızda ki işlemi iptal etmek için çalıştıracağımız fonksiyonumuz.
        self.my_client.stop(self.name)

    def remove(self):
        # containerımızı silecek fonksiyonumuz
        state = self.my_client.inspect_container(self.name)
        state = state['State']['Running']
        if state is True:
            self.my_client.stop(self.name)
        self.my_client.remove_container(self.name)
        self.volumes = []
        self.binds = {}
        self.name = None
        if self.package_name is not None:
            shutil.rmtree('/tmp/gonullu/%s' % self.package_name, ignore_errors=True)
            shutil.rmtree('/tmp/varpisi/%s' % self.package_name, ignore_errors=True)
            self.package_name = None

    def get_logs(self):
        # burada oluşan log çıktılarımızı yakalayacağız.
        self.my_client.logs(self.name)

    def set_name(self, name):
        # container adımızı atadığımız fonksiyonumuz.
        dictionary = 'abcdefghijklmnopqrstuvxyzABCDEFGHIJKLMNOPQRSTUVXYZ-_1234567890'
        dictionary_len = len(dictionary)
        self.package_name = name
        self.name = ''
        for i in name:
            if i not in dictionary:
                i = dictionary[random.randint(1, dictionary_len)]
            self.name += str(i)

    @staticmethod
    def set_memory_limit(memory_limit):
        # ram limitimizi atadığımız fonksiyonumuz.
        return int((psutil.virtual_memory().total * (memory_limit / 100))) >> 20

    def set_image(self, image):
        # imajımızı atadığımız fonksiyonumuz.
        self.image = image

    @staticmethod
    def set_cpu_set(cpu_set):
        # atayacağımız cpularımızı atadığımız fonksiyonumuz.
        return int(cpu_set)

    def add_volume(self, local, indocker):
        # bölüm ekleyeceğimiz fonksiyonumuz.
        self.volumes.append(indocker)
        self.binds[local] = {'bind': indocker, 'mode': 'rw'}

    def set_command(self, application, queue_id, commit_id, package):
        # çalıştıracağımız komutu atadığımız fonksiyonumuz.
        self.command = '%s %s %s %s' % (application, queue_id, commit_id, package)

    def check(self):
        # derleme işlemi devam ediyor mu kontrol edelim
        for container in self.my_client.containers():
            if container['Names'][0].replace('/', '') == self.name:
                return 0
        else:
            return 1

    def control_docker(self):
        # oluşacak paketin adı ile önceden docker kaydı var mı kontrol edelim.
        for container in self.my_client.containers(all=True):
            if container['Names'][0].replace('/', '') == self.name:
                self.remove()

    def exit_signal(self, signal, frame):
        if self.name is not None:
            self.remove()

        self.log.blank_line()
        self.log.warning(message='CTRL+C\'ye tıkladınız!')
        self.log.get_exit()

from django.core.files.storage import FileSystemStorage
from fdfs_client.client import Fdfs_client


class FdfsStorage(FileSystemStorage):
    """自定义文件存储"""

    def _save(self, name, content):
        """用户上传图片到网站时，Django会自动调用
        此方法将图片保存只fastdfs存储设备中"""

        # 把用户上传的图片，通过fastdfs的api，上传到fastdfs服务器
        client = Fdfs_client('/dailyfresh/utils/fastdfs/client.conf')

        # 返回文件在fastdfs服务器中的路径
        try:
            data = content.read()
            json = client.upload_by_buffer(data)
            print(json.get('Status'))
        except Exception as e:
            raise e  # 不直接捕获异常，抛出去由调用者进行处理

        # if 'Upload successed.' != json.get('status'):
        #     #上传失败
        #     raise  Exception('Fastdfs上传文件失败，status不正确')

        if json.get('Status') == 'Upload successed.':
            path = json.get('Remote file_id')
            print(path)
        else:
            print('出错了')

        #获取id
        return path

    def url(self, name):
        """重写url方法"""
        host = 'http://127.0.0.1:8888/'
        return host + super().url(name)




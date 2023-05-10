import requests
import json
import socketserver
import config

# Конфиг сокет-сервера
HOST = "127.0.0.1"  # IP сокетсервера, в нашем случае лупбек
PORT = 65432  # Порт конкретно этого парсера, !!вынести в энвы!!

# Конфиг парсера
api_url = "https://api.vk.com/method/"
api_version = "5.131"
access_token = config.ACCESS_TOKEN

# Кастомная функция получения всей payload
def recvall(sock):
    """Функция для получения всего сообщения целиком из сокета

    Args:
        sock (_type_): сокет

    Returns:
        _type_: Цельное сообщение из сокета
    """
    BUFF_SIZE = 4096  # 4 KiB
    data = b""
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        if len(part) < BUFF_SIZE:
            # either 0 or end of data
            break
    return data


def getChannelSubscribers(group_id: int) -> dict:
    """Функция получения количества подписчиков в группе

    Args:
        group_id (int): ID Группы

    Returns:
        dict: Возвращает dict содержащий число подписчиков по ключу 'subscribers'
    """
    res = requests.get(
        f"{api_url}groups.getMembers?group_id={group_id}&count=0&access_token={access_token}&v={api_version}"
    )
    return {"subscribers": json.loads(res.text)["response"]["count"]}


def getChannelLastPosts(group_id: int, count: int = 100) -> dict:
    """Получение информации по N последним постам в группе

    Args:
        group_id (int): ID Группы
        count (int, optional): Количество последних постов которые нужно получить. По умолчанию 100.

    Returns:
        dict: Возвращает dict с информацией о постах, ключи: comments,date,likes,reposts,views,text,photos,photos
    """
    assert count <= 100
    res = requests.get(
        f"{api_url}wall.get?owner_id={-group_id}&count={count}&access_token={access_token}&v={api_version}"
    )
    res = json.loads(res.text)["response"]["items"]
    data = []
    for post in res:
        post_data = {}
        post_data["comments"] = post["comments"]["count"]
        post_data["date"] = post["date"]
        post_data["likes"] = post["likes"]["count"]
        post_data["reposts"] = post["reposts"]["count"]
        post_data["views"] = post["views"]["count"]
        post_data["text"] = post["text"]
        post_data["photos"] = []
        for attachment in post["attachments"]:
            if attachment["type"] != "photo":
                continue
            post_data["photos"].append(
                max(attachment["photo"]["sizes"], key=lambda x: x["height"])["url"]
            )

        data.append(post_data)
    return data


class MyTCPHandler(socketserver.BaseRequestHandler):
    """Класс сокет-сервера

    Args:
        socketserver (_type_): Родительский класс из библеотеки
    """

    def handle(self):
        """Обработчик соединения
        """
        # Читаем реквест целиком
        task = json.loads(recvall(self.request))

        # По умолчанию отправляем ошибку
        res = {"type": "error", "data":{"error":"method not found"}}

        # Разбор вариантов
        if task["method"] == "subs":
            # Меняем тип колбека на успешный
            res["type"] = "success"
            # Вызываем нужную функцию
            res["data"] = getChannelSubscribers(task["data"])
            
        elif task["method"] == "posts":
            res["type"] = "success"
            res["data"] = getChannelLastPosts(task["data"]["channel_id"], task["data"]["count"])
            

        # Отправляем результат
        self.request.sendall(str.encode(json.dumps(res)))


# # Поднимаем сокет-сервер
if __name__ == "__main__":
    with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
        server.serve_forever()

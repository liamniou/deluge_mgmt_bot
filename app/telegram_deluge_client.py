import os

from dataclasses import dataclass
from deluge_client import DelugeRPCClient


DELUGE_HOST = os.getenv("DELUGE_HOST")
DELUGE_PORT = int(os.getenv("DELUGE_PORT", "58846"))
DELUGE_USERNAME = os.getenv("DELUGE_USERNAME", "localclient")
DELUGE_PASSWORD = os.getenv("DELUGE_PASSWORD")
ADMINS = [x for x in os.getenv("ADMINS", "294967926").split(",")]


def hr_time_duration(seconds):
    TIME_DURATION_UNITS = (
        ("h", 60 * 60),
        ("m", 60),
        ("s", 1),
    )

    if seconds == 0:
        return "???"
    parts = []
    for unit, div in TIME_DURATION_UNITS:
        amount, seconds = divmod(int(seconds), div)
        if amount > 0:
            parts.append("{}{}".format(amount, unit))
    return ":".join(parts)


@dataclass
class Torrent:
    id: str
    name: str
    state: str
    eta: int
    progress: int
    eta_hr: str = ""

    def __post_init__(self):
        self.eta_hr = (
            f"({hr_time_duration(self.eta)} ETA)" if self.state == "Downloading" else ""
        )
        self.progress = round(self.progress)


class TelegramDelugeClient:
    def __init__(self, tg_user_id):
        self.client = DelugeRPCClient(
            DELUGE_HOST, DELUGE_PORT, DELUGE_USERNAME, DELUGE_PASSWORD
        )
        self.client.connect()
        self.tg_user_id = str(tg_user_id)

    def parse_torrents(self):
        torrents_list = self.client.core.get_torrents_status({}, {})
        parsed_torrents = []

        for id, data in torrents_list.items():
            if (
                self.tg_user_id in ADMINS
                or data["label".encode("utf-8")].decode() == self.tg_user_id
            ):
                parsed_torrents.append(
                    Torrent(
                        id.decode(),
                        data["name".encode("utf-8")].decode(),
                        data["state".encode("utf-8")].decode(),
                        data["eta".encode("utf-8")],
                        data["progress".encode("utf-8")],
                    )
                )

        return parsed_torrents

    def delete_torrent_by_name(self, torrent_name):
        torrents = self.parse_torrents()

        for t in torrents:
            if t.name == torrent_name:
                try:
                    self.client.core.remove_torrent(torrent_id=t.id, remove_data=True)
                    print("Torrent removed")
                    return
                except:
                    print(f"Can't find {torrent_name}")
        print(f"Can't find {torrent_name}")

    def add_torrent(self, magnet_link):
        try:
            torrent_id = self.client.core.add_torrent_magnet(magnet_link, {})
            print("Torrent added")
        except:
            print("Can't add the torrent. Try again")
            return

        try:
            self.create_label_if_missing(self.tg_user_id)
            self.client.label.set_torrent(
                torrent_id=torrent_id, label_id=self.tg_user_id
            )
        except:
            print("Failed to apply the label")
        return torrent_id

    def pause_torrent_by_name(self, torrent_name):
        torrents = self.parse_torrents()

        for t in torrents:
            if t.name == torrent_name:
                try:
                    self.client.core.pause_torrent(torrent_id=t.id)
                    print("Torrent paused")
                    return
                except:
                    print(f"Failed to pause {torrent_name}")
        print(f"Can't find {torrent_name}")

    def resume_torrent_by_name(self, torrent_name):
        torrents = self.parse_torrents()

        for t in torrents:
            if t.name == torrent_name:
                try:
                    self.client.core.resume_torrent(torrent_id=t.id)
                    print(f"Torrent {torrent_name} resumed")
                    return
                except:
                    print(f"Failed to resume {torrent_name}")
        print(f"Can't find {torrent_name}")

    def create_label_if_missing(self, label_name):
        labels = self.client.label.get_labels()
        for label in labels:
            if label.decode() == label_name:
                return
        self.client.label.add(label_name)

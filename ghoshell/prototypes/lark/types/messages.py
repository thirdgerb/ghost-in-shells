from abc import ABCMeta
from typing import ClassVar, List, Dict

from pydantic import BaseModel, Field


class LarkMsg(BaseModel, metaclass=ABCMeta):
    """
    标准的 lark 消息类型.
    """

    msg_type: ClassVar[str] = ""


class LarkText(LarkMsg):
    """
    文本消息
    """

    msg_type: ClassVar[str] = "text"
    text: str


# 以下代码由 LLM 生成.


class ImageMsg(LarkMsg):
    """
    图片类型的消息
    """
    msg_type: ClassVar[str] = "image"

    image_key: str = Field(description="图片key")


class FileMsg(LarkMsg):
    """
    文件类型的消息
    """
    msg_type: ClassVar[str] = "file"

    file_key: str = Field(description="")
    file_name: str = Field(description="文件名")


class FolderMsg(LarkMsg):
    """
    文件夹类型的消息
    """
    msg_type: ClassVar[str] = "folder"

    file_key: str = Field(description="")
    file_name: str = Field(description="文件夹名称")


class AudioMsg(LarkMsg):
    """
    音频类型的消息
    """
    msg_type: ClassVar[str] = "audio"

    file_key: str = Field(description="文件key")
    duration: int = Field(description="时长 毫秒级")


class MediaMsg(LarkMsg):
    """
    视频类型的消息
    """
    msg_type: ClassVar[str] = "media"

    file_key: str = Field(description="文件key")
    image_key: str = Field(description="视频封面图片key")
    file_name: str = Field(description="文件名")
    duration: int = Field(description="视频时长 毫秒级")


class StickerMsg(LarkMsg):
    """
    表情包类型的消息
    """
    msg_type: ClassVar[str] = "sticker"

    file_key: str = Field(description="表情包的文件 key")


class HongbaoMsg(LarkMsg):
    """
    红包类型的消息
    """
    msg_type: ClassVar[str] = "hongbao"

    text: str = Field(description="红包")


class ShareCalendarEventMsg(LarkMsg):
    """
    日程分享卡片类型的消息
    """
    msg_type: ClassVar[str] = "share_calendar_event"

    summary: str = Field(description="日程摘要")
    start_time: str = Field(description="开始时间（毫秒级时间戳）")
    end_time: str = Field(description="结束时间（毫秒级时间戳）")


class CalendarMsg(LarkMsg):
    """
    日程邀请卡片类型的消息
    """
    msg_type: ClassVar[str] = "calendar"

    summary: str = Field(description="日程摘要")
    start_time: str = Field(description="开始时间，毫秒级时间戳")
    end_time: str = Field(description="结束时间，毫秒级时间戳")


class ShareChatMsg(LarkMsg):
    """
    群名片类型的消息
    """
    msg_type: ClassVar[str] = "share_chat"

    chat_id: str = Field(description="群聊 ID")


class SystemMsg(LarkMsg):
    """
    系统消息类型
    """
    msg_type: ClassVar[str] = "system"

    template: str = Field(description="消息模板")
    from_user: List = Field(description="发送消息的用户")
    to_chatters: List = Field(description="接收消息的用户")


class LocationMsg(LarkMsg):
    """
    位置类型的消息
    """
    msg_type: ClassVar[str] = "location"

    name: str = Field(description="")
    longitude: str = Field(description="经度")
    latitude: str = Field(description="纬度")


class VideoChatMsg(LarkMsg):
    """
    视频通话消息
    """
    msg_type: ClassVar[str] = "video_chat"

    topic: str = Field(description="视频通话消息")
    start_time: str = Field(description="毫秒级时间戳")


class VoteMsg(LarkMsg):
    """
    投票类型的消息
    """
    msg_type: ClassVar[str] = "vote"

    topic: str = Field(description="投票主题")
    options: List[str] = Field(description="选项内容列表")


class PostMsg(LarkMsg):
    """
    富文本类型的消息
    """
    msg_type: ClassVar[str] = "post"

    title: str = Field(description="标题消息")
    content: List[List[Dict]] = Field(description="消息内容, 由多行组成, 每一行又由若干个小块组成",
                                      default_factory=list)


class InteractiveMsg(LarkMsg):
    """
    可互动的消息.
    """

    msg_type: ClassVar[str] = "interactive"
    title: str = Field(description="卡片标题")
    elements: List[List[Dict]] = Field(description="卡片的元素", default_factory=list)


class TodoMsg(LarkMsg):
    """
    任务类型的消息
    """
    msg_type: ClassVar[str] = "todo"

    task_id: str = Field(description="任务ID，使用此ID可以对任务进行操作，详情参见任务概述")
    summary: PostMsg = Field(description="富文本格式的任务标题")
    due_time: str = Field(description="任务截止时间的毫秒级时间戳")

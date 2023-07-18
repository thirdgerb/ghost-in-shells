from abc import ABCMeta
from typing import ClassVar, List

from pydantic import BaseModel, Field


class PostInfo(BaseModel, metaclass=ABCMeta):
    """
    富文本类型的消息体.
    """
    tag: ClassVar[str] = ""


class TextInfo(PostInfo):
    """
    字符串类型消息
    """
    tag: ClassVar = "text"
    text: str = Field(description="文本内容")
    un_escape: bool = Field(description="表示是不是 unescape 解码")
    style: List = Field(
        description="文本内容的加粗、下划线、删除线和斜体样式，可选值分别为bold、underline、lineThrough与italic，没有样式则为空列表",
        enum={"bold", "underline", "lineThrough", "italic"}
    )


class AInfo(PostInfo):
    """
    a 类型的消息
    """
    tag: ClassVar = "a"
    text: str = Field(description="链接显示的文本内容")
    href: str = Field(description="链接地址")
    style: List = Field(
        description="文本内容的加粗、下划线、删除线和斜体样式，可选值分别为bold、underline、lineThrough与italic，没有样式则为空列表",
        enum={"bold", "underline", "lineThrough", "italic"}
    )


class AtInfo(PostInfo):
    """
    at 类型的消息
    """
    tag: ClassVar = "at"
    user_id: str = Field(description="被at用户的open_id")
    user_name: str = Field(description="用户姓名")
    style: List = Field(
        description="文本内容的加粗、下划线、删除线和斜体样式，可选值分别为bold、underline、lineThrough与italic，没有样式则为空列表",
        enum={"bold", "underline", "lineThrough", "italic"}
    )


class ImageInfo(PostInfo):
    """
    img 类型的消息
    """
    tag: ClassVar = "img"
    image_key: str = Field(description="图片的唯一标识")


class MediaInfo(PostInfo):
    """
    media 类型的消息
    """
    tag: ClassVar = "media"
    file_key: str = Field(description="视频文件的唯一标识")
    image_key: str = Field(description="视频封面图片的唯一标识")


class EmotionInfo(PostInfo):
    """
    emotion 类型的消息
    """
    tag: ClassVar = "emotion"
    emoji_type: str = Field(description="表情类型， 部分可选值请参见表情文案",
                            enum={"smile", "happy", "sad", "angry", "cry", "laugh"})

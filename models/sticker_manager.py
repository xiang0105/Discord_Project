# sticker_manager.py
# 管理伺服器內貼圖查詢與選擇

class StickerManager:
    @staticmethod
    def build_sticker_map(guild):
        # 回傳 name->StickerObject 字典
        mapping = {}
        if not guild:
            return mapping
        if guild.stickers:
            for s in guild.stickers:
                mapping[s.name] = s
        return mapping
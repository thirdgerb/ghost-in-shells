from __future__ import annotations

# class AttendImpl(Attend):
#
#     def __init__(self, ctx: Context, this: Thought):
#         self.ctx = ctx
#         self.this = this
#         self._attentions: List[Attention] = []
#
#     def to_stages(self, *stages) -> Attend:
#         intentions = self.ctx.clone.intentions
#         think = intentions.force_fetch(self.this.url.resolver)
#         fr = self.this.url.dict()
#         for stage_name in stages:
#             stage = think.fetch_stage(stage_name)
#             if stage is None:
#                 continue
#             stage_intentions = stage.intentions(self.ctx)
#             if stage_intentions is not None:
#                 attention = Attention(
#                     to=self.this.url.to_dict(stage=stage_name),
#                     intentions=[intention.dict() for intention in stage_intentions],
#                     fr=fr,
#                     level=self.this.level,
#                 )
#                 self._attentions.append(attention)
#         return self
#
#     def to_think(self, think_name: str, args: Dict | None) -> Attend:
#         intentions = self.ctx.clone.intentions
#         think = intentions.force_fetch(think_name)
#         intentions = think.intentions(self.ctx)
#         fr = self.this.url.to_dict(args=args)
#         if intentions is not None:
#             attention = Attention(
#                 to=think.url().dict(),
#                 intentions=[intention.dict() for intention in intentions],
#                 fr=fr,
#                 level=self.this.level,
#             )
#             self._attentions.append(attention)
#         return self
#
#     def intentions(self) -> List[Attention] | None:
#         if len(self._attentions) == 0:
#             return None
#         result = self._attentions
#         del self.ctx
#         del self.this
#         del self._attentions
#         return result

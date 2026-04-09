"""Safety and policy enforcement layer."""

class SafetyGuard :
    def filter_text (self,text:str) ->str:
        text= "".join(text.split())
        return text[:120]
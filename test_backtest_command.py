import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock classes for Telegram components
class MockMessage:
    def __init__(self, text):
        self.text = text
    
    async def edit_text(self, text, *args, **kwargs):
        print(f"\n[EDITED MESSAGE OUTPUT]:\n{text.encode('ascii', 'backslashreplace').decode('ascii')}")
        return self

class MockUpdate:
    class MockEffectiveUser:
        name = "TestUser"
    
    class MockEffectiveChat:
        id = 12345
        
    def __init__(self):
        self.effective_user = self.MockEffectiveUser()
        self.effective_chat = self.MockEffectiveChat()
        self.message = self
        
    async def reply_text(self, text, *args, **kwargs):
        print(f"\n[INITIAL REPLY]: {text.encode('ascii', 'backslashreplace').decode('ascii')}")
        return MockMessage(text)

class MockContext:
    def __init__(self, args):
        self.args = args

async def test_backtest():
    print("Testing backtest_command with ASELS for 90 days...")
    from main import backtest_command
    update = MockUpdate()
    context = MockContext(args=["ASELS", "90"])
    await backtest_command(update, context)

if __name__ == "__main__":
    asyncio.run(test_backtest())

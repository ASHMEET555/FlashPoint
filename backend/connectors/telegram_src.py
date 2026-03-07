"""Telegram Channel Streaming Connector for FlashPoint Intelligence Pipeline

Connects to Telegram using persistent session authentication.
Streams real-time messages from monitored channels + backfills recent history.

Features:
- Async/await event-driven architecture
- Session persistence (no re-auth required)
- Dual-mode: historical backfill + live streaming
- Message metadata extraction (sender, URL, timestamp)
"""

import asyncio
import pathway as pw
from telethon import TelegramClient, events


class TelegramSource(pw.io.python.ConnectorSubject):
    """
    Pathway-compatible streaming connector for Telegram.

    This connector:
    - Connects to Telegram using a persisted session
    - Backfills recent message history
    - Streams new messages in real time
    - Emits structured rows directly into the Pathway dataflow
    """

    def __init__(self, api_id, api_hash, phone, channels=None, bias_tags=None, 
                 backfill_limit=20, polling_interval=60):
        """
        Initialize the Telegram connector.

        Args:
            api_id (int): Telegram API ID
            api_hash (str): Telegram API hash
            phone (str): Phone number associated with the Telegram account
            channels (list): List of channel handles to monitor
            bias_tags (dict): Dictionary mapping channel handles to bias tags
            backfill_limit (int): Number of historical messages to fetch per channel
            polling_interval (int): Interval for polling / housekeeping (unused for live events)
        """
        super().__init__()
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.polling_interval = polling_interval
        self.backfill_limit = backfill_limit
        
        # Default channels if none provided
        if channels is None:
            channels = ["intelslava", "insider_paper", "disclosetv", "DefenderDome"]
        
        self.channels = channels
        
        # Default bias tags if none provided
        if bias_tags is None:
            bias_tags = {handle: "Independent" for handle in channels}
        
        self.bias_tags = bias_tags
        
        # Track already-seen messages if deduplication is needed
        self.seen_messages = set()

    def run(self):
        """
        Entry point invoked by Pathway.

        This method:
        - Creates an isolated asyncio event loop
        - Connects to Telegram using Telethon
        - Loads recent message history
        - Subscribes to live message events indefinitely
        """
        # ========== ASYNC SETUP ==========
        # 2. Setup Async Loop (isolated event loop for this connector)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # ========== CLIENT INITIALIZATION ==========
        # 3. Initialize Client
        # Uses a persistent session file ("session_flashpoint")
        # so authentication is not required on every startup.
        client = TelegramClient('session_flashpoint', self.api_id, self.api_hash)

        # ========== LIVE MESSAGE HANDLER ==========
        # 4. Define Handler (For Live Data)
        # Triggered automatically whenever a new message arrives
        @client.on(events.NewMessage(chats=self.channels))
        async def handler(event):
            await self._process_message(event, "LIVE")

        # ========== MAIN EXECUTION SEQUENCE ==========
        # 5. Define Main Logic
        async def main_sequence():
            print(f"🔌 [Telegram] Connecting using saved session for {self.phone}...")
            
            # Because you already logged in, this will verify the session file 
            # and connect IMMEDIATELY without asking for code/phone.
            await client.start(phone=self.phone)
            
            print("✅ [Telegram] CONNECTED! (Session Valid)")

            # ========== HISTORICAL BACKFILL ==========
            # --- FETCH REAL HISTORY ---
            print(f"📜 [Telegram] Fetching last {self.backfill_limit} messages per channel...")
            for channel in self.channels:
                try:
                    # Get last messages from real history
                    async for message in client.iter_messages(channel, limit=self.backfill_limit):
                        if message and message.text:
                            await self._process_message(message, "HISTORY")
                except Exception as e:
                    print(f"⚠️ [Telegram] Error reading {channel}: {e}")

            # ========== LIVE STREAMING ==========
            # --- LISTEN FOREVER ---
            print("👀 [Telegram] History loaded. Listening for new breaking news...")
            await client.run_until_disconnected()

        # ========== EVENT LOOP EXECUTION ==========
        # 6. Run Execution
        try:
            loop.run_until_complete(main_sequence())
        except KeyboardInterrupt:
            pass

    async def _process_message(self, event, tag):
        """Helper to format data for Pathway
        
        Extracts message metadata and normalizes to unified event schema.
        
        Args:
            event: Telethon message event
            tag: Origin tag ("LIVE" or "HISTORY")
        """
        # ========== METADATA EXTRACTION ==========
        # Get sender information
        sender = await event.get_sender()
        username = sender.username if sender else "Unknown"
        
        # Clean text for console preview (truncate and remove newlines)
        text_clean = str(event.text).replace('\n', ' ')[:60]
        
        # ========== NORMALIZE TO UNIFIED SCHEMA ==========
        # Build structured record for Pathway
        row = {
            "source": "Telegram",
            "text": str(event.text),
            "url": f"https://t.me/{username}/{event.id}",
            "timestamp": float(event.date.timestamp()),
            "bias": self.bias_tags.get(username, "Unknown")  # Look up bias tag by channel
        }
        
        # Emit row into Pathway dataflow
        self.next(**row)
        
        # ========== LOGGING ==========
        # Lightweight logging for observability
        print(f"⚡ [{tag}] {username}: {text_clean}...", flush=True)

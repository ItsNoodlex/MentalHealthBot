# Overview

This is a Discord bot written in Python that provides comprehensive mental health support functionality for Discord servers. The bot features scheduled daily check-ins with mood tracking, anonymous venting capabilities, and moderation tools. It's designed to create a supportive environment for mental health discussions while maintaining user privacy and security.

# User Preferences

Preferred communication style: Simple, everyday language.
Setup wizard preference: Original playful, interactive text-based setup with message deletion and casual tone.
Help system preference: !help for admin setup guidance, !commands for command list only.

# System Architecture

## Core Architecture
- **Language**: Python 3.x
- **Framework**: discord.py library with commands extension
- **Data Storage**: Local JSON files for persistence
- **Deployment**: Designed for Replit hosting environment
- **Bot Type**: Discord application bot with message handling, reactions, and scheduled tasks

## File Structure
```
/
├── main.py                    # Main bot application (incomplete)
├── settings.json              # Per-server configuration storage
├── last_messages.json         # Message tracking for deletion/cleanup
├── sticky_messages.json       # Vent channel sticky message management
├── dismissed_users.json       # User-specific dismissal tracking
├── anon_logs.json            # Anonymous message logs (encrypted)
├── access_codes.json         # One-time access codes for log viewing
├── moderator_access.json     # Moderator permission tracking
└── attached_assets/          # Backups and example data
```

# Key Components

## Bot Configuration
- **Intents**: Configured for message content, guilds, and members access
- **Command Prefix**: Uses '!' for text commands
- **Help System**: Custom help command disabled (custom implementation)

## Data Management Systems
1. **Settings Storage**: Per-server JSON configuration allowing customizable behavior per guild
2. **Message Tracking**: Persistent storage of last messages for cleanup functionality
3. **User State Management**: Tracking of dismissed users for personalized experiences
4. **Security Layer**: Anonymous logging with encryption using hashlib, base64, and secrets modules

## Core Features
1. **Daily Check-ins**: Scheduled mental health mood tracking with emoji reactions
2. **Anonymous Venting**: Secure anonymous message posting with privacy protection
3. **Moderation Tools**: Access code system for viewing anonymous logs
4. **Sticky Messages**: Automated sticky message management in vent channels
5. **Multi-Server Support**: Independent configuration per Discord server

# Data Flow

## Anonymous Message Flow
1. User posts anonymous message in vent channel
2. Message content is encrypted and stored in anon_logs.json
3. Original message is deleted for privacy
4. Encoded data includes timestamp, user hash, and encrypted content
5. Access codes are generated for moderation review when needed

## Daily Check-in Flow
1. Scheduled task triggers at configured time per server
2. Bot posts check-in message in designated post channel
3. Users react with mood emojis for tracking
4. Results are processed and stored for analytics

## Server Configuration Flow
1. Admins use setup commands to configure channels and settings
2. Settings are stored per-server in settings.json
3. Each server maintains independent configuration for:
   - Post channel (daily check-ins)
   - Support channel (general support)
   - Vent channel (anonymous messages)
   - Ping preferences and timezone settings

# External Dependencies

## Required Python Packages
- **discord.py**: Main Discord bot framework
- **datetime**: Time handling for scheduling
- **json**: Data persistence and configuration
- **os**: File system operations
- **asyncio**: Asynchronous operations
- **random**: Random code generation
- **secrets**: Cryptographically secure random generation
- **hashlib**: Message hashing for privacy
- **base64**: Encoding for data obfuscation
- **pytz**: Timezone handling (imported but may not be fully implemented)

## Discord API Integration
- Bot requires Discord application with bot token
- Needs appropriate permissions for message management, reactions, and channel access
- Uses Discord's gateway for real-time message handling

# Deployment Strategy

## Replit Environment
- Designed for continuous hosting on Replit platform
- Uses local file storage for data persistence
- JSON files provide simple, readable data storage
- No external database dependencies

## Security Considerations
- Anonymous message encryption protects user privacy
- Access code system prevents unauthorized log viewing
- Per-server isolation ensures data separation
- Hash-based user identification for anonymity

## Scalability Approach
- File-based storage suitable for small to medium Discord servers
- Per-server configuration allows horizontal scaling across multiple guilds
- Modular design supports feature additions without major refactoring

Note: The main.py file appears to be incomplete in the repository, containing only the initial imports and setup code. The attached_assets folder contains what appears to be a more complete version of the code and example data showing the bot's functionality in action.
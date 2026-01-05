async def handle_setup_response(message, session):
    """Handle setup wizard responses"""
    guild = message.guild
    channel = message.channel
    user = message.author
    content = message.content.strip()
    step = session['step']
    
    try:
        if step == 2:  # Post channel selection
            target_channel = await parse_channel(guild, content)
            if not target_channel:
                embed = discord.Embed(
                    title="❌ Invalid Channel",
                    description="Please mention a valid text channel or type the channel name (e.g., #general or general)",
                    color=0xff0000
                )
                await channel.send(embed=embed, delete_after=5)
                return
            
            session['data']['post_channel'] = target_channel.id
            session['step'] = 3
            
            embed = discord.Embed(
                title="Setup Wizard - Step 3/6 📞",
                description="**Noice! Now pick your support channel** 💬\n\nThis is where people can go when they need some extra love and support. You know, for when the going gets tough and they need a hug (but in text form).\n\n*Pro tip: Don't use your meme channel for this one 😅*\n\n**Please mention the support channel or type its name:**",
                color=0x7289da
            )
            embed.set_footer(text="Example: #support or support")
            await session['message'].edit(embed=embed)
            
        elif step == 3:  # Support channel selection
            target_channel = await parse_channel(guild, content)
            if not target_channel:
                embed = discord.Embed(
                    title="❌ Invalid Channel",
                    description="Please mention a valid text channel or type the channel name (e.g., #support or support)",
                    color=0xff0000
                )
                await channel.send(embed=embed, delete_after=5)
                return
            
            session['data']['support_channel'] = target_channel.id
            session['step'] = 4
            
            embed = discord.Embed(
                title="Setup Wizard - Step 4/6 🫣",
                description="**Sweet! Now let's set up the secret diary channel** 📝\n\nThis is where people can anonymously spill their thoughts without anyone knowing who's doing the spilling. It's like a confession booth, but cooler and with more emojis.\n\n*Warning: May contain feelings*\n\n**Please mention the vent channel or type its name:**",
                color=0x7289da
            )
            embed.set_footer(text="Example: #vent or anonymous-vent")
            await session['message'].edit(embed=embed)
            
        elif step == 4:  # Vent channel selection
            target_channel = await parse_channel(guild, content)
            if not target_channel:
                embed = discord.Embed(
                    title="❌ Invalid Channel",
                    description="Please mention a valid text channel or type the channel name (e.g., #vent or anonymous-vent)",
                    color=0xff0000
                )
                await channel.send(embed=embed, delete_after=5)
                return
            
            session['data']['vent_channel'] = target_channel.id
            session['step'] = 5
            
            embed = discord.Embed(
                title="Setup Wizard - Step 5/6 📣",
                description="**Awesome sauce! Who should I annoy... I mean, *notify* for check-ins?** 🔔\n\nPick your poison wisely - some people love a good @everyone, others prefer the gentle nudge of @here. Choose your chaos level!\n\n**Type one of the following:**\n• `@everyone` - Ping everyone (maximum chaos)\n• `@here` - Ping only online members (medium chaos)\n• `none` - No pings (peaceful mode)",
                color=0x7289da
            )
            embed.set_footer(text="Choose wisely...")
            await session['message'].edit(embed=embed)
            
        elif step == 5:  # Ping selection
            ping_options = {
                '@everyone': '@everyone',
                'everyone': '@everyone',
                '@here': '@here',
                'here': '@here',
                'none': 'none',
                'no': 'none'
            }
            
            ping_choice = ping_options.get(content.lower())
            if not ping_choice:
                embed = discord.Embed(
                    title="❌ Invalid Option",
                    description="Please type one of: `@everyone`, `@here`, or `none`",
                    color=0xff0000
                )
                await channel.send(embed=embed, delete_after=5)
                return
            
            session['data']['ping'] = ping_choice
            session['step'] = 6
            
            embed = discord.Embed(
                title="Setup Wizard - Step 6/6 ⏰",
                description="**Final step! When should I send the daily check-ins?** 🕐\n\nPick a time that works for your community. Maybe when people are having their morning coffee, or when they're winding down for the day.\n\n**Please enter a time in 24-hour format:**\n• Examples: `09:00`, `14:30`, `20:15`\n• Must be in HH:MM format",
                color=0x7289da
            )
            embed.set_footer(text="Example: 09:00 for 9 AM")
            await session['message'].edit(embed=embed)
            
        elif step == 6:  # Time selection
            try:
                time_parts = content.split(':')
                if len(time_parts) != 2:
                    raise ValueError
                hour, minute = int(time_parts[0]), int(time_parts[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
                time_str = f"{hour:02d}:{minute:02d}"
            except ValueError:
                embed = discord.Embed(
                    title="❌ Invalid Time",
                    description="Please enter a valid time in HH:MM format (e.g., 09:00, 14:30, 20:15)",
                    color=0xff0000
                )
                await channel.send(embed=embed, delete_after=5)
                return
            
            session['data']['time'] = time_str
            session['data']['timezone'] = 'UTC'
            
            server_settings[str(guild.id)] = session['data']
            save_data()
            
            post_ch = guild.get_channel(int(session['data']['post_channel']))
            support_ch = guild.get_channel(int(session['data']['support_channel']))
            vent_ch = guild.get_channel(int(session['data']['vent_channel']))
            
            embed = discord.Embed(
                title="🎉 Setup Complete! Welcome to Wholesome-ville!",
                description="**Congrats! Your server is now 1000% more supportive!** 💖\n\nI'm all configured and ready to help your community check in on each other and share their feelings safely.",
                color=0x00ff7f
            )
            embed.add_field(
                name="📅 Daily Check-ins",
                value=f"Every day at **{time_str} UTC** in {post_ch.mention}\nPeople can react with emojis to show how they're feeling!",
                inline=False
            )
            embed.add_field(
                name="💬 Support Hub",
                value=f"{support_ch.mention}\nFor deeper conversations and peer support",
                inline=False
            )
            embed.add_field(
                name="🫣 Anonymous Venting",
                value=f"{vent_ch.mention}\nSafe space for anonymous feelings (with mod oversight)",
                inline=False
            )
            embed.add_field(
                name="🔔 Daily Ping Style",
                value=f"**{session['data']['ping']}** - {'Everyone gets notified!' if session['data']['ping'] == '@everyone' else 'Only online members get notified!' if session['data']['ping'] == '@here' else 'Silent mode - no pings!'}",
                inline=False
            )
            embed.set_footer(text="Thanks for setting up mental health support for your community! 💙")
            
            await session['message'].edit(embed=embed)
            
            await setup_vent_channel(vent_ch, str(guild.id))
            
            guild_id_str = str(guild.id)
            user_id_str = str(user.id)
            del setup_sessions[guild_id_str][user_id_str]
            if not setup_sessions[guild_id_str]:
                del setup_sessions[guild_id_str]
                
    except Exception as e:
        print(f"Error in setup wizard step {step}: {e}")
        embed = discord.Embed(
            title="❌ Setup Error", 
            description=f"Something went wrong at step {step}. Please try the `!setup` command again.",
            color=0xff0000
        )
        await channel.send(embed=embed, delete_after=10)
        
        guild_id = str(guild.id)
        user_id = str(user.id)
        if guild_id in setup_sessions and user_id in setup_sessions[guild_id]:
            del setup_sessions[guild_id][user_id]
            if not setup_sessions[guild_id]:
                del setup_sessions[guild_id]
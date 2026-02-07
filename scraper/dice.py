            print(f"\n[3/5] Scraping Luma for {location}...")
            print("-" * 70)
            try:
                # Convert location to Luma format
                location_to_luma = {
                    # dictionary content should be here
                }
                print(f"✓ Luma total: {len(luma_events)} events")
            except Exception as e:
                print(f"✗ Error scraping Luma: {e}")

        # ===== DICE.FM SCRAPING =====
    if config.get("MODES", {}).get("ENABLE_DICE_FM_SCRAPING", True):
        print(f"\n[4/5] Scraping Dice.fm for {location}...")
        print("-" * 70)
        try:
            from dice_fm import scrape_dice_fm
            
            # Get max price from config, default to free only (0)
            max_price = config.get("SOURCES", {}).get("DICE_FM", {}).get("max_price", 0)
            
            dice_events = await scrape_dice_fm(location, max_price)
            all_events.extend(dice_events)
            existing_links.update(e.get('link', '') for e in dice_events)
            print(f"✓ Dice.fm total: {len(dice_events)} events")
        except Exception as e:
            print(f"✗ Error scraping Dice.fm: {e}")
    
    # ===== RA.CO SCRAPING =====
    if config.get("MODES", {}).get("ENABLE_RA_CO_SCRAPING", True):
        print(f"\n[5/5] Scraping RA.co for {location}...")
        print("-" * 70)
        try:
            from ra_co import scrape_ra_co
            
            # Get fetch_details flag from config
            fetch_details = config.get("SOURCES", {}).get("RA_CO", {}).get("fetch_detail_pages", True)
            
            ra_events = await scrape_ra_co(location, fetch_details=fetch_details)
            all_events.extend(ra_events)
            existing_links.update(e.get('link', '') for e in ra_events)
            print(f"✓ RA.co total: {len(ra_events)} events")
        except Exception as e:
            print(f"✗ Error scraping RA.co: {e}")
    
    # ===== MERGE AND SAVE =====
    print(f"\n[4/4] Merging results...")
    print("-" * 70)
    #line107



           except Exception as e:
            print(f"✗ Error scraping RA.co: {e}")
    
    # ===== MERGE AND SAVE =====
    print(f"\n[4/4] Merging results...")
    print(f"\n[6/6] Merging results...")
    print("-" * 70)
    
    # Load existing events from all_events.json
    existing_merged = {}
   #line191



   
  #line230
   
    print("\nSummary:")
    eventbrite_count = len([e for e in all_events_final if e.get('source') == 'Eventbrite'])
    meetup_count = len([e for e in all_events_final if e.get('source') == 'Meetup'])
    luma_count = len([e for e in all_events_final if e.get('source') == 'Luma'])
    dice_count = len([e for e in all_events_final if e.get('source') == 'Dice.fm'])
    ra_count = len([e for e in all_events_final if e.get('source') == 'RA.co'])
    
    print(f"  Eventbrite events: {eventbrite_count}")
    print(f"  Meetup events: {meetup_count}")
    print(f"  Luma events: {luma_count}")
    print(f"  Dice.fm events: {dice_count}")
    print(f"  RA.co events: {ra_count}")
    print(f"  Total unique: {len(all_events_final)}")
    
    print("\nFiles created/updated:")
    print("  - all_events.json")
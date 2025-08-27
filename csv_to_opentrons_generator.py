#!/usr/bin/env python3
"""
Opentrons Protocol Generator from CSV
====================================
This script generates Opentrons OT-2 protocol code from CSV files containing
liquid handling instructions. It automatically segments data into batches of
28 wells or less and handles volume-based pipette selection.

Usage:
    python csv_to_opentrons_generator.py

Configuration:
    - Modify CSV_FILE_PATH to point to your CSV file
    - Adjust METADATA and other parameters as needed
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import json

# Configuration
CSV_FILE_PATH = r"c:\Users\User\Downloads\Protocol.py2\Updated_V_gly_V_NaCl_combinations-Tris-A1_D4.csv"
OUTPUT_FILE_PATH = r"c:\Users\User\Downloads\Protocol.py2\Generated_Protocol.py"

# Protocol metadata
METADATA = {
    "protocolName": "Auto-Generated Cloud Point Protocol",
    "author": "Python Generator",
    "description": "Auto-generated dilution series for CP test from CSV data",
    "apiLevel": "2.24"
}

# Liquid definitions
LIQUID_DEFINITIONS = {
    "glycine": {
        "name": "2.4M Glycine",
        "description": "in water",
        "color": "#b925ff",
        "tube_position": "A1"
    },
    "nacl": {
        "name": "5M NaCl", 
        "description": "in water",
        "color": "#ffd600",
        "tube_position": "A2"
    },
    "tris": {
        "name": "500mM Tris buffer",
        "description": "in water", 
        "color": "#7eff42ff",
        "tube_position": "B1"
    },
    "water": {
        "name": "water",
        "description": "",
        "color": "#50d5ffff",
        "tube_position": "B2"
    }
}

def read_csv_data(file_path):
    """Read and parse CSV data"""
    try:
        df = pd.read_csv(file_path)
        print(f"Successfully loaded CSV with {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

def filter_valid_wells(df):
    """Filter out wells with negative water volumes"""
    # Check if water column exists
    water_cols = [col for col in df.columns if 'water' in col.lower()]
    if not water_cols:
        print("Warning: No water volume column found")
        return df
    
    water_col = water_cols[0]
    initial_count = len(df)
    
    # Filter positive water volumes
    df_filtered = df[df[water_col] > 0].copy()
    filtered_count = len(df_filtered)
    
    print(f"Filtered {initial_count - filtered_count} wells with negative water volumes")
    print(f"Remaining wells: {filtered_count}")
    
    return df_filtered

def segment_data(df, max_wells=28):
    """Segment data into batches of maximum 28 wells"""
    segments = []
    total_rows = len(df)
    
    for i in range(0, total_rows, max_wells):
        segment = df.iloc[i:i+max_wells].copy()
        segments.append(segment)
        print(f"Segment {len(segments)}: {len(segment)} wells")
    
    return segments

def get_well_positions(df):
    """Extract or generate well positions"""
    # Look for well position column
    position_cols = [col for col in df.columns if any(x in col.lower() for x in ['well', 'position', 'pos'])]
    
    if position_cols:
        return df[position_cols[0]].tolist()
    
    # Generate well positions if not found
    wells = []
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    cols = list(range(1, 13))
    
    well_idx = 0
    for _, row in df.iterrows():
        if well_idx < len(rows) * len(cols):
            row_idx = well_idx // len(cols)
            col_idx = well_idx % len(cols) + 1
            wells.append(f"{rows[row_idx]}{col_idx}")
            well_idx += 1
        else:
            wells.append(f"X{well_idx}")  # Overflow handling
            well_idx += 1
    
    return wells

def identify_columns(df):
    """Identify relevant columns in the CSV"""
    columns = {}
    
    # Column mapping patterns
    patterns = {
        'glycine': ['gly', '2.4m', 'glycine'],
        'nacl': ['nacl', '5m', 'salt'],
        'tris': ['tris', 'buffer', '0.5m'],
        'water': ['water', 'h2o']
    }
    
    for liquid, pattern_list in patterns.items():
        for col in df.columns:
            if any(pattern in col.lower() for pattern in pattern_list):
                columns[liquid] = col
                break
    
    print(f"Identified columns: {columns}")
    return columns

def generate_protocol_header(segment_num=1, total_segments=1, wells_in_segment=28):
    """Generate protocol header and imports"""
    timestamp = datetime.now().isoformat()
    
    protocol_name = METADATA['protocolName']
    if total_segments > 1:
        protocol_name += f" - Segment {segment_num}/{total_segments}"
    
    header = f'''import json
from opentrons import protocol_api, types

metadata = {{
    "protocolName": "{protocol_name}",
    "author": "{METADATA['author']}",
    "description": "{METADATA['description']} (Segment {segment_num}: {wells_in_segment} wells)",
    "created": "{timestamp}",
    "lastModified": "{timestamp}",
    "protocolDesigner": "Python Generator",
    "source": "CSV Auto-Generator",
}}

requirements = {{"robotType": "OT-2", "apiLevel": "{METADATA['apiLevel']}"}}

def run(protocol: protocol_api.ProtocolContext) -> None:
'''
    return header

def generate_labware_section():
    """Generate labware loading section"""
    labware = '''    # Load Labware:
    tip_rack_1 = protocol.load_labware(
        "opentrons_96_filtertiprack_20ul",
        location="2",
        namespace="opentrons",
        version=1,
    )
    tip_rack_2 = protocol.load_labware(
        "opentrons_96_filtertiprack_200ul",
        location="3",
        namespace="opentrons",
        version=1,
    )
    tube_rack_1 = protocol.load_labware(
        "opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical",
        location="1",
        namespace="opentrons",
        version=2,
    )
    well_plate_1 = protocol.load_labware(
        "corning_96_wellplate_360ul_flat",
        location="4",
        namespace="opentrons",
        version=3,
    )
    tip_rack_3 = protocol.load_labware(
        "opentrons_96_filtertiprack_20ul",
        location="5",
        label="Opentrons OT-2 96 Filter Tip Rack 20 µL (1)",
        namespace="opentrons",
        version=1,
    )
    tip_rack_4 = protocol.load_labware(
        "opentrons_96_filtertiprack_200ul",
        location="6",
        label="Opentrons OT-2 96 Filter Tip Rack 200 µL (1)",
        namespace="opentrons",
        version=1,
    )

    # Load Pipettes:
    pipette_right = protocol.load_instrument(
        "p20_single_gen2", "right", tip_racks=[tip_rack_1, tip_rack_3],
    )
    pipette_left = protocol.load_instrument(
        "p300_single_gen2", "left", tip_racks=[tip_rack_2, tip_rack_4],
    )
'''
    return labware

def generate_liquid_definitions():
    """Generate liquid definitions section"""
    liquids = "    # Define Liquids:\n"
    
    for i, (key, liquid) in enumerate(LIQUID_DEFINITIONS.items(), 1):
        liquids += f'''    liquid_{i} = protocol.define_liquid(
        "{liquid['name']}",
        description="{liquid['description']}",
        display_color="{liquid['color']}",
    )
'''
    
    liquids += "\n    # Load Liquids:\n"
    for i, (key, liquid) in enumerate(LIQUID_DEFINITIONS.items(), 1):
        liquids += f'''    tube_rack_1.load_liquid(
        wells=["{liquid['tube_position']}"],
        liquid=liquid_{i},
        volume=10000,
    )
'''
    
    return liquids

def select_pipette(volume):
    """Select appropriate pipette based on volume"""
    if volume <= 20:
        return "pipette_right", "p20_single_gen2"
    else:
        return "pipette_left", "p300_single_gen2"

def generate_liquid_class(step_name, pipette_type, volume):
    """Generate liquid class definition"""
    
    if pipette_type == "p20_single_gen2":
        tip_rack = "opentrons/opentrons_96_filtertiprack_20ul/1"
        flow_rate = 7.56
    else:
        tip_rack = "opentrons/opentrons_96_filtertiprack_200ul/1"
        flow_rate = 46.4
    
    return f'''        liquid_class=protocol.define_liquid_class(
            name="{step_name}",
            properties={{"{pipette_type}": {{"{tip_rack}": {{
                "aspirate": {{
                    "aspirate_position": {{
                        "offset": {{"x": 0, "y": 0, "z": 55}},
                        "position_reference": "well-bottom",
                    }},
                    "flow_rate_by_volume": [(0, {flow_rate})],
                    "pre_wet": False,
                    "correction_by_volume": [(0, 0)],
                    "delay": {{"enabled": False}},
                    "mix": {{"enabled": False}},
                    "submerge": {{
                        "delay": {{"enabled": False}},
                        "speed": 125,
                        "start_position": {{
                            "offset": {{"x": 0, "y": 0, "z": 2}},
                            "position_reference": "well-top",
                        }},
                    }},
                    "retract": {{
                        "air_gap_by_volume": [(0, 0)],
                        "delay": {{"enabled": False}},
                        "end_position": {{
                            "offset": {{"x": 0, "y": 0, "z": 2}},
                            "position_reference": "well-top",
                        }},
                        "speed": 125,
                        "touch_tip": {{"enabled": False}},
                    }},
                }},
                "dispense": {{
                    "dispense_position": {{
                        "offset": {{"x": 0, "y": 0, "z": 3}},
                        "position_reference": "well-bottom",
                    }},
                    "flow_rate_by_volume": [(0, {flow_rate})],
                    "delay": {{"enabled": True, "duration": 2}},
                    "submerge": {{
                        "delay": {{"enabled": False}},
                        "speed": 125,
                        "start_position": {{
                            "offset": {{"x": 0, "y": 0, "z": 2}},
                            "position_reference": "well-top",
                        }},
                    }},
                    "retract": {{
                        "air_gap_by_volume": [(0, 0)],
                        "delay": {{"enabled": False}},
                        "end_position": {{
                            "offset": {{"x": 0, "y": 0, "z": 2}},
                            "position_reference": "well-top",
                        }},
                        "speed": 125,
                        "touch_tip": {{
                            "enabled": True,
                            "z_offset": -1,
                            "mm_from_edge": 0,
                            "speed": 60,
                        }},
                        "blowout": {{"enabled": True, "location": "destination", "flow_rate": {flow_rate}}},
                    }},
                    "correction_by_volume": [(0, 0)],
                    "push_out_by_volume": [(0, 5)],
                    "mix": {{"enabled": True, "repetitions": 5, "volume": {min(20, volume//2)}}},
                }},
            }}}}}},
        ),'''

def generate_transfer_step(step_num, volume, source_tube, dest_wells, liquid_name, columns):
    """Generate a single transfer step"""
    
    pipette, pipette_type = select_pipette(volume)
    
    # Build source list
    source_list = f'[tube_rack_1["{source_tube}"]' + f', tube_rack_1["{source_tube}"]' * (len(dest_wells) - 1) + ']'
    
    # Build destination list
    dest_list = '[' + ', '.join([f'well_plate_1["{well}"]' for well in dest_wells]) + ']'
    
    step = f'''
    # Step {step_num}:
    {pipette}.transfer_with_liquid_class(
        volume={volume},
        source={source_list},
        dest={dest_list},
        new_tip="always",
        trash_location=protocol.fixed_trash,
        keep_last_tip=True,
{generate_liquid_class(f"transfer_step_{step_num}", pipette_type, volume)}
    )
    {pipette}.drop_tip()
'''
    
    return step

def group_by_reagent_and_volume(df, columns, well_positions):
    """Group transfers by reagent type and volume for efficient liquid handling"""
    transfers = []
    
    # Process each reagent type
    reagent_order = ['tris', 'nacl', 'glycine', 'water']
    
    for reagent in reagent_order:
        if reagent not in columns:
            continue
            
        col_name = columns[reagent]
        source_tube = LIQUID_DEFINITIONS[reagent]['tube_position']
        
        # Group by volume
        volume_groups = df.groupby(col_name)
        
        for volume, group in volume_groups:
            if volume <= 0:
                continue
                
            # Get well positions for this volume
            wells = [well_positions[idx] for idx in group.index]
            
            transfers.append({
                'reagent': reagent,
                'volume': volume,
                'source_tube': source_tube,
                'wells': wells,
                'count': len(wells)
            })
    
    return transfers

def generate_protocol_steps_for_segment(df_segment, columns, segment_idx=1):
    """Generate protocol steps for a single segment"""
    steps = ""
    step_counter = 1
    
    # Get well positions for this segment
    well_positions = get_well_positions(df_segment)
    
    # Reset index for proper mapping
    df_segment = df_segment.reset_index(drop=True)
    
    # Group transfers by reagent and volume
    transfers = group_by_reagent_and_volume(df_segment, columns, well_positions)
    
    # Generate steps for each transfer
    for transfer in transfers:
        if transfer['count'] > 0:
            step = generate_transfer_step(
                step_counter,
                transfer['volume'],
                transfer['source_tube'],
                transfer['wells'],
                transfer['reagent'],
                columns
            )
            steps += step
            step_counter += 1
    
    return steps

def generate_full_protocol(csv_path):
    """Generate complete protocol from CSV, creating separate files for each segment"""
    
    print(f"Processing CSV file: {csv_path}")
    
    # Read and process data
    df = read_csv_data(csv_path)
    if df is None:
        return None
    
    # Filter valid wells
    df_filtered = filter_valid_wells(df)
    
    # Identify columns
    columns = identify_columns(df_filtered)
    
    # Segment data
    segments = segment_data(df_filtered)
    total_segments = len(segments)
    
    # Generate protocol files for each segment
    generated_files = []
    
    for segment_idx, df_segment in enumerate(segments):
        segment_num = segment_idx + 1
        wells_in_segment = len(df_segment)
        
        # Create unique filename for each segment
        if total_segments > 1:
            # Extract directory and filename without extension
            output_dir = os.path.dirname(OUTPUT_FILE_PATH)
            base_filename = os.path.splitext(os.path.basename(OUTPUT_FILE_PATH))[0]
            segment_file_path = os.path.join(output_dir, f"{base_filename}_Segment_{segment_num}.py")
        else:
            segment_file_path = OUTPUT_FILE_PATH
        
        # Ensure the directory exists
        output_dir = os.path.dirname(segment_file_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        print(f"Generating Segment {segment_num}/{total_segments}: {wells_in_segment} wells -> {os.path.basename(segment_file_path)}")
        
        # Generate protocol sections for this segment
        protocol_code = generate_protocol_header(segment_num, total_segments, wells_in_segment)
        protocol_code += generate_labware_section()
        protocol_code += generate_liquid_definitions()
        protocol_code += f"\n    # PROTOCOL STEPS - SEGMENT {segment_num}/{total_segments} ({wells_in_segment} wells)\n"
        protocol_code += generate_protocol_steps_for_segment(df_segment, columns, segment_idx)
        
        # Write segment file
        try:
            with open(segment_file_path, 'w', encoding='utf-8') as f:
                f.write(protocol_code)
            generated_files.append(segment_file_path)
            print(f"✅ Segment {segment_num} saved successfully")
        except Exception as e:
            print(f"❌ Error writing segment {segment_num}: {e}")
    
    return generated_files

def main():
    """Main function"""
    print("=== Opentrons Protocol Generator ===")
    print(f"Input CSV: {CSV_FILE_PATH}")
    print(f"Output Base: {OUTPUT_FILE_PATH}")
    
    # Check if input file exists
    if not os.path.exists(CSV_FILE_PATH):
        print(f"Error: CSV file not found at {CSV_FILE_PATH}")
        print("Please update CSV_FILE_PATH in the script configuration")
        return
    
    # Generate protocol
    generated_files = generate_full_protocol(CSV_FILE_PATH)
    
    if generated_files:
        print(f"\n✅ Protocol generation completed!")
        print(f"📁 Generated {len(generated_files)} protocol file(s):")
        for i, file_path in enumerate(generated_files, 1):
            lines = 0
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
            except:
                pass
            print(f"   {i}. {os.path.basename(file_path)} ({lines} lines)")
        print(f"\n� Summary:")
        print(f"   - Total segments: {len(generated_files)}")
        print(f"   - Max wells per file: 28")
        print(f"   - Ready for Opentrons execution")
    else:
        print("❌ Failed to generate protocol")

if __name__ == "__main__":
    main()

# Additional utility functions for customization
def update_csv_path(new_path):
    """Update the CSV file path"""
    global CSV_FILE_PATH
    CSV_FILE_PATH = new_path
    print(f"Updated CSV path to: {new_path}")

def update_metadata(name=None, author=None, description=None):
    """Update protocol metadata"""
    if name:
        METADATA['protocolName'] = name
    if author:
        METADATA['author'] = author  
    if description:
        METADATA['description'] = description
    print(f"Updated metadata: {METADATA}")

# Example usage:
# update_csv_path(r"path/to/your/csv/file.csv")
# update_metadata(name="My Custom Protocol", author="My Name")
# main()

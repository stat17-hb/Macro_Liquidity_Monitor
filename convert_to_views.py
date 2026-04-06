import os
import glob
import re

import sys

def convert():
    if not os.path.exists("views"):
        os.makedirs("views")
    
    pages = glob.glob("pages/*.py")
    
    mapping = {
        "1_Executive_Overview.py": "overview.py",
        "2_Balance_Sheet.py": "balance_sheet.py",
        "3_Collateral.py": "collateral.py",
        "4_Marginal_Belief.py": "marginal_belief.py",
        "5_Leverage.py": "leverage.py",
        "6_Alerts.py": "alerts.py",
        "7_QT_Monitoring.py": "qt_monitoring.py"
    }
    
    for page in pages:
        filename = os.path.basename(page)
        if filename not in mapping:
            continue
            
        with open(page, "r", encoding="utf-8") as f:
            content = f.read()
            
        # remove st.set_page_config
        content = re.sub(r'st\.set_page_config\([^)]+\)', '', content, flags=re.DOTALL)
        
        # remove global CSS import and apply
        content = re.sub(r'# Apply global CSS\nfrom components\.styles import get_global_css\nst\.markdown\(get_global_css\(\), unsafe_allow_html=True\)', '', content)
        
        # We also need to find where the main logic starts.
        # Usually it's right after getting data from session state, or after render_page_header
        
        lines = content.split('\n')
        new_lines = []
        is_import_section = True
        
        for line in lines:
            if "if 'data_dict' not in st.session_state:" in line:
                break
            
            # keep imports
            new_lines.append(line)
            
        # Now we define the function
        func_name = "render_" + mapping[filename].replace(".py", "")
        
        new_lines.append(f"\ndef {func_name}(data_dict, regime_result=None):")
        new_lines.append("    # Get data from args instead of session state")
        new_lines.append("    if not data_dict:")
        new_lines.append("        st.warning('⚠️ 데이터가 없습니다.')")
        new_lines.append("        return")
        new_lines.append("    ")
        
        # Find where data_dict is assigned from session state and skip to next
        body_started = False
        for i, line in enumerate(lines):
            if not body_started:
                if "data_dict = st.session_state" in line or "data_dict = st.session_state.get('data_dict'" in line:
                    body_started = True
                continue
            
            # If we see regime_result = st.session_state..., we skip
            if "regime_result = st.session_state" in line:
                continue
            
            # Note: 1_Executive_Overview uses regime_history_df from session state
            if "regime_history_df = st.session_state" in line:
                new_lines.append("    " + line)
                continue
            
            new_lines.append("    " + line)
            
        
        with open(os.path.join("views", mapping[filename]), "w", encoding="utf-8") as f:
            f.write('\n'.join(new_lines))

if __name__ == "__main__":
    convert()

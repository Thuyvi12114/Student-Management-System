import xml.etree.ElementTree as ET
import pandas as pd

tree = ET.parse("ketqua.xml")
root = tree.getroot()

rows = []
for tc in root.iter("testcase"):
    status = "PASSED"
    detail = ""

    failure = tc.find("failure")
    error = tc.find("error")
    skipped = tc.find("skipped")

    if failure is not None:
        status = "FAILED"
        detail = failure.attrib.get("message", "")
    elif error is not None:
        status = "ERROR"
        detail = error.attrib.get("message", "")
    elif skipped is not None:
        status = "SKIPPED"
        detail = skipped.attrib.get("message", "")

    rows.append({
        "Class / File": tc.attrib.get("classname", ""),
        "Test Case": tc.attrib.get("name", ""),
        "Time (s)": tc.attrib.get("time", ""),
        "Status": status,
        "Detail": detail,
    })

df = pd.DataFrame(rows)
df.to_excel("tong_hop_ket_qua.xlsx", index=False)
print(f"Da ghi {len(rows)} ket qua test vao tong_hop_ket_qua.xlsx!")

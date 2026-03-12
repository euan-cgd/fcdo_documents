icai = r"\bicai\b|independent.?commission.?for.?aid.?impact"

def extract_windows(text, pattern, window_size=400):
    matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
    windows = []

    # Create initial windows
    for match in matches:
        start = max(0, match.start() - window_size)
        end = min(len(text), match.end() + window_size)
        windows.append((start, end))

    # Merge overlapping windows
    if not windows:
        return ""

    # Sort windows by start
    windows.sort(key=lambda x: x[0])
    merged_windows = [windows[0]]

    for current_start, current_end in windows[1:]:
        last_start, last_end = merged_windows[-1]
        if current_start <= last_end:  # Overlapping or contiguous
            merged_windows[-1] = (last_start, max(last_end, current_end))  # Merge
        else:
            merged_windows.append((current_start, current_end))

    # Extract text for merged windows
    extracted_sections = []
    for start, end in merged_windows:
        snippet = text[start:end]
        snippet = re.sub(r'\s+', ' ', snippet).strip()
        extracted_sections.append(snippet)

    return "\n\n".join(extracted_sections)


bc['icai'] = bc.TEXT.str.contains(icai,regex=True,case=False,na=False).astype(int)
adds['icai'] = adds.TEXT.str.contains(icai,regex=True,case=False,na=False).astype(int)

bc["icai_num"] = [len(re.findall(icai,txt.lower())) for txt in bc.TEXT]
adds["icai_num"] = [len(re.findall(icai,txt.lower())) for txt in adds.TEXT]

windows = []
for i in range(bc.shape[0]):
    if bc.icai_num.iloc[i]>0:
        toadd = extract_windows(bc.TEXT.iloc[i],icai,window_size=400)
        windows.append(toadd)
    else:
        windows.append("na")
bc['icai_window'] = windows
bc['year'] = bc['narrative'].str.extract(r'published[^\)]*(\d{4})')
bc = pd.merge(bc,dat,on="parent",how="left")
bc['qau'] = bc.budget_sum>40000000

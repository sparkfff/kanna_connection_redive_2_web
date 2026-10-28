"""Carry time and conservative, whole-day attack classification."""


def carry_seconds(hp, damage, start_time, battle_time):
    """ceil(110 - elapsed * hp / raw_damage), using exact integer arithmetic.

    Formula: watermellye/pcr_calculator_plus, pcr_calculator.py:solve_equation.
    Only a normal 90s attack can earn another carryover.
    """
    if (start_time != 90 or not isinstance(hp, int) or not isinstance(damage, int)
            or not 0 < hp <= damage or not isinstance(battle_time, int)
            or not 0 <= battle_time <= start_time):
        return 0
    return min(90, 110 - battle_time * hp // damage)


def own_units(record):
    try:
        return frozenset(int(value) for value in (record.own_units or '').split(',') if value)
    except (ValueError, AttributeError):
        return frozenset()


def _day_states(records, respect_policy=True):
    """Enumerate the legal daily sequences and their unconsumed tokens.

    A full attack or tail consumes one of three daily starts. A carry consumes
    an earned token and cannot earn a second token. Own units cannot be reused
    in a new start; borrowed units are excluded before storage. Missing history
    is tolerated for identifiable short/manual/policy carryovers. Ambiguous
    90s attacks retain their original classification rather than moving the
    error to the last attack of the day.
    """
    records = list(records)
    if len(records) > 12:
        return set()
    # (normal starts, pending (length, originating row, own units), flags)
    states = {(0, (), ())}
    used = frozenset()
    for index, record in enumerate(records):
        units = own_units(record)
        reused_units = units & used
        reused = bool(reused_units)
        used |= units
        start = record.remain_time
        source = record.knife_source or ''
        killed = bool(record.kill_confirmed or (source == '' and record.flag == 1))
        tail = killed or record.battle_time < start
        forced_carry = start < 90 or respect_policy and source == 'policy' and not killed or source == 'manual' and record.flag == .5
        forced_normal = source == 'manual' and record.flag != .5
        next_states = set()
        earned = carry_seconds(record.boss_hp, record.raw_damage, start, record.battle_time)
        for starts, tokens, flags in states:
            if not forced_carry and start == 90 and starts < 3 and (not reused or forced_normal):
                flag = record.flag if forced_normal else 1 if tail else 0
                new_tokens = (*tokens, (earned, index, units)) if killed or forced_normal and flag == 1 else tokens
                next_states.add((starts + 1, new_tokens, (*flags, flag)))
            if not forced_normal:
                # A zero token represents a confirmed tail with unknown length.
                matches = {i for i, (length, _, original_units) in enumerate(tokens)
                           if length in (0, start) and reused_units <= original_units}
                for i in matches:
                    next_states.add((starts, tokens[:i] + tokens[i+1:], (*flags, .5)))
                if forced_carry and not matches:
                    next_states.add((starts, tokens, (*flags, .5)))
        states = next_states
        if not states or len(states) > 2048:
            return set()
    return states


def classify_day(records):
    """Return only classifications shared by every legal daily sequence."""
    records = list(records)
    states = _day_states(records)
    if not states:
        return {}
    result = {}
    for i, record in enumerate(records):
        flags = {state[2][i] for state in states}
        if len(flags) == 1:
            flag = flags.pop()
            seconds = carry_seconds(record.boss_hp, record.raw_damage, record.remain_time, record.battle_time) if flag == 1 else 0
            result[i] = (flag, seconds)
    return result


def remaining_carries(records):
    """Remaining amounts by length, without claiming ambiguous tokens are free.

    The lower/upper bounds count unconsumed tokens in all legal sequences;
    identical-length tokens remain countable even if their origin is unclear.
    None means the history cannot support a reliable reconstruction.
    """
    records = list(records)
    if len({record.time for record in records}) != len(records):
        return None
    # First-day mode changes statistics, not actual carry ownership.
    states = _day_states(records, respect_policy=False)
    if not states:
        return None
    counts = []
    for _, tokens, _ in states:
        lengths = {}
        for seconds, _, _ in tokens:
            lengths[seconds] = lengths.get(seconds, 0) + 1
        counts.append(lengths)
    seconds = sorted({seconds for count in counts for seconds in count}, reverse=True)
    return [(seconds, min(count.get(seconds, 0) for count in counts),
             max(count.get(seconds, 0) for count in counts)) for seconds in seconds]

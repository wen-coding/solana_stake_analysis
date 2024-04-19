""" Runs simulation on current Solana stakes."""
import argparse
import numpy as np

def read_stakes(filename):
    '''Reads stakes from file.'''
    result = []
    file = open(filename, "r", encoding="utf-8")
    for line in file.readlines():
        result.append(float(line))
    file.close()
    return result

def analyze_stakes(stakes, original_sum):
    '''Return sum and number of validators with how/low stakes.'''
    total = 0
    high_stakes = 0
    low_stakes = 0
    high_stake_limit = original_sum * 0.003
    low_stake_limit = original_sum * 0.00002
    for stake in stakes:
        total += stake
        if stake > high_stake_limit:
            high_stakes += 1
        elif stake < low_stake_limit:
            low_stakes += 1
    return total, high_stakes, low_stakes

def select_stakes(stakes, target_stake_sum, candidates=None):
    '''Selects stakes, the sum should no greater but as close as possible to target_stake_sum.'''
    current_sum = 0
    result = set()
    if candidates is not None:
        select_from = list(candidates)
        select_from.sort()
    else:
        select_from = list(range(len(stakes)))
    smallest_stake = stakes[select_from[0]]
    biggest_candidate = stakes[select_from[-1]]
    for _ in range(len(stakes)):
        while select_from and stakes[select_from[-1]] > target_stake_sum - current_sum:
            select_from.pop()
        if not select_from:
            break
        index = np.random.choice(select_from)
        stake = stakes[index]
        current_sum += stake
        result.add(index)
        select_from.remove(index)
        if stake == smallest_stake and select_from:
            smallest_stake = stakes[select_from[0]]
        if current_sum >= target_stake_sum or current_sum + smallest_stake > target_stake_sum:
            break
    return result, current_sum, biggest_candidate

def perform_simulation(stakes, non_conforming_indices, samples, rotation, rounds):
    '''Performs simulation on stakes.'''
    sum_stakes = sum(stakes)
    count_stakes = len(stakes)
    prob = np.array(stakes)/sum_stakes
    mins = {}
    maxs = {}
    non_conforming_counts = [0, 0, 0] # over 1/3, 1/2, 2/3
    states = {}
    for i in range(count_stakes):
        states[i] = 0
    choices = []
    serving = set()
    rotate_number = 0
    for round_index in range(rounds):
        if round_index % 1000 == 0:
            print(f"round {round_index}")
        select_count = samples if len(choices) == 0 else rotate_number
        available = []
        available_prob = []
        for i in range(count_stakes):
            if states[i] == 0:
                available.append(i)
                available_prob.append(prob[i])
            elif states[i] == 2:
                states[i] = 0
        total_available_prob = sum(available_prob)
        choice_indices = np.random.choice(
            available,
            size=select_count,
            replace=False,
            p=np.array(available_prob)/total_available_prob)
        for i in choice_indices:
            states[i] = 1
            serving.add(i)
            choices.append(stakes[i])
        stakes_stats = analyze_stakes(choices, sum_stakes)
        for (j, value) in enumerate(stakes_stats):
            mins[j] = min(mins.get(j, value), value)
            maxs[j] = max(maxs.get(j, value), value)
        non_conforming_ratio = sum(stakes[i] for i in serving if i in non_conforming_indices)
        non_conforming_ratio = non_conforming_ratio/stakes_stats[0]
        mins['non_conforming'] = min(
            mins.get('non_conforming', non_conforming_ratio), non_conforming_ratio)
        maxs['non_conforming'] = max(
            maxs.get('non_conforming', non_conforming_ratio), non_conforming_ratio)
        if non_conforming_ratio > 2/3:
            non_conforming_counts[2] += 1
        elif non_conforming_ratio > 1/2:
            non_conforming_counts[1] += 1
        elif non_conforming_ratio > 1/3:
            non_conforming_counts[0] += 1
        stakes_to_rotate = stakes_stats[0] * rotation / 100
        remove_indices, removed_stakes, biggest_candidate = select_stakes(
            stakes, stakes_to_rotate, serving)
        biggest_candidate = biggest_candidate/stakes_stats[0]
        mins['biggest_candidate'] = min(
            mins.get('biggest_candidate', biggest_candidate), biggest_candidate)
        maxs['biggest_candidate'] = max(
            maxs.get('biggest_candidate', biggest_candidate), biggest_candidate)
        if removed_stakes > stakes_to_rotate * 1.01:
            print("Error: removed_stakes", removed_stakes, "stakes_to_rotate", stakes_to_rotate)
        rotate_number = len(remove_indices)
        mins['rotate_number'] = min(mins.get('rotate_number', rotate_number), rotate_number)
        maxs['rotate_number'] = max(maxs.get('rotate_number', rotate_number), rotate_number)
        for i in remove_indices:
            states[i] = 2
            serving.remove(i)
            choices.remove(stakes[i])   
    return mins, maxs, non_conforming_counts

def interpolate_stakes(stakes, interpolate):
    '''Interpolates stakes to specified number of validators.'''
    count_stakes = len(stakes)
    if count_stakes >= interpolate:
        return stakes
    x = np.linspace(0, count_stakes-1, num=count_stakes)
    xnew = np.linspace(0, count_stakes-1, num=interpolate-count_stakes)
    interpolated = np.interp(xnew, x, stakes)
    result = stakes + interpolated.tolist()
    result.sort()
    return result

def main(args):
    '''Main function.'''
    print("args", args)
    original_stakes = read_stakes("./validators_stakes_epoch_600")
    original_stakes = interpolate_stakes(original_stakes, args.interpolate)
    sum_original_stakes = sum(original_stakes)
    non_conforming, _, _ = select_stakes(
        original_stakes, sum(original_stakes) * args.non_conforming / 100)
    _, original_highstake, original_lowstake = analyze_stakes(
        original_stakes, sum_original_stakes)
    print(f"total stake {sum_original_stakes} high_stakes (>0.3%) {original_highstake} "
        f"low_stakes (<0.002%) {original_lowstake}")
    print(f"random sampling {args.samples} out of {len(original_stakes)}, "
        f"{args.rounds} rounds rotating {args.rotation}% stakes every round")
    range_mins, range_maxs, non_conformings = perform_simulation(
        original_stakes, non_conforming, args.samples, args.rotation, args.rounds)
    print(f"total {range_mins[0]*100/sum_original_stakes:2.2f}% to "
        f"{range_maxs[0]*100/sum_original_stakes:2.2f}% high_stakes(>0.3%) "
        f"{range_mins[1]} to {range_maxs[1]} low_stakes(<0.002%%) "
        f"{range_mins[2]} to {range_maxs[2]}")
    print(f"non_conforming {range_mins['non_conforming']*100:2.2f}% to "
        f"{range_maxs['non_conforming']*100:2.2f}%")
    print(f"non_conforming (1/3 ~ 1/2) {non_conformings[0]}"
        f"(1/2 ~ 2/3) {non_conformings[1]}"
        f"(> 2/3) {non_conformings[2]}")
    print(f"biggest_candidate {range_mins['biggest_candidate']*100:2.2f}% to "
          f"{range_maxs['biggest_candidate']*100:2.2f}% rotate_number "
          f"{range_mins['rotate_number']} to {range_maxs['rotate_number']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Perform simulation on Solana stakes.')
    parser.add_argument('--samples', dest='samples', default=200, type=int,
                        help='Number of samples in each round (default to 200)')
    parser.add_argument('--rounds', dest='rounds', default=1000, type=int,
                        help='Number of rounds in simulation (default to 1000)')
    parser.add_argument('--rotation', dest='rotation', default=10, type=int,
                        help='Percentage of stake rotation on each round (default to 10)')
    parser.add_argument('--non_conforming', dest='non_conforming', default=5, type=int,
                        help='Percent of non-conforming validators (default to 5)')
    parser.add_argument('--interpolate', dest='interpolate', default=10000, type=int,
                        help='Interpolate to specified number of validators (default to 10000)')
    main(parser.parse_args())

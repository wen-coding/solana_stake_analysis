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
    high_stake_limit = original_sum * 0.01
    low_stake_limit = original_sum * 0.0001
    for stake in stakes:
        total += stake
        if stake > high_stake_limit:
            high_stakes += 1
        elif stake < low_stake_limit:
            low_stakes += 1
    return total, high_stakes, low_stakes

def select_non_conforming_stakes(stakes, target_stake_sum):
    '''Selects non-conforming stakes, the sum should close to target_stake_sum (within 10%).'''
    current_sum = 0
    result = set()
    for i in range(10000*len(stakes)):
        index = np.random.randint(0, len(stakes))
        if index in result:
            continue
        stake = stakes[index]
        if current_sum + stake > target_stake_sum * 1.0001:
            continue
        current_sum += stake
        result.add(index)
        if current_sum >= target_stake_sum:
            break
    return result

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
    serving = []
    rotate_number = samples * rotation // 100
    for _ in range(rounds):
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
            serving.append(i)
            choices.append(stakes[i])
        stakes_stats = analyze_stakes(choices, sum_stakes)
        for (j, value) in enumerate(stakes_stats):
            mins[j] = min(mins.get(j, value), value)
            maxs[j] = max(maxs.get(j, value), value)
        non_conforming_ratio = sum(stakes[i] for i in non_conforming_indices)/stakes_stats[0]
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
        remove_indices = np.random.choice(serving, size=rotate_number, replace=False)
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
    return stakes + interpolated.tolist()

def main(args):
    '''Main function.'''
    print("args", args)
    original_stakes = read_stakes("./validators_stakes_epoch_600")
    original_stakes = interpolate_stakes(original_stakes, args.interpolate)
    sum_original_stakes = sum(original_stakes)
    non_conforming = select_non_conforming_stakes(
        original_stakes, sum(original_stakes) * args.non_conforming / 100)
    _, original_highstake, original_lowstake = analyze_stakes(
        original_stakes, sum_original_stakes)
    print(f"total stake {sum_original_stakes} high_stakes (>1%) {original_highstake} "
        f"low_stakes (<0.01%) {original_lowstake}")
    print(f"random sampling {args.samples} out of {len(original_stakes)}, "
        f"{args.rounds} rounds rotating {args.rotation}% stakes every round")
    range_mins, range_maxs, non_conformings = perform_simulation(
        original_stakes, non_conforming, args.samples, args.rotation, args.rounds)
    print(f"total {range_mins[0]*100/sum_original_stakes:2.2f}% to "
        f"{range_maxs[0]*100/sum_original_stakes:2.2f}% high_stakes(>1%) "
        f"{range_mins[1]} to {range_maxs[1]} low_stakes(<0.01%%) "
        f"{range_mins[2]} to {range_maxs[2]}")
    print(f"non_conforming {range_mins['non_conforming']*100:2.2f}% to "
        f"{range_maxs['non_conforming']*100:2.2f}%")
    print(f"non_conforming (1/3 ~ 1/2) {non_conformings[0]*100/args.rounds:2.2f}% "
        f"(1/2 ~ 2/3) {non_conformings[1]*100/args.rounds:2.2f}% "
        f"(> 2/3) {non_conformings[2]*100/args.rounds:2.2f}%")

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
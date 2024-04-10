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
    return [total, high_stakes, low_stakes]

parser = argparse.ArgumentParser(description='Perform simulation on Solana stakes.')
parser.add_argument('--samples', dest='samples', default=200, type=int,
                    help='Number of samples in each round (default to 200)')
parser.add_argument('--rounds', dest='rounds', default=1000, type=int,
                    help='Number of rounds in simulation (default to 1000)')
args = parser.parse_args()
original_stakes = read_stakes("./validators_stakes_epoch_600")
sum_stakes = sum(original_stakes)
original = analyze_stakes(original_stakes, sum_stakes)
print(f"total stake {sum_stakes} high_stakes (>1%) {original[1]} low_stakes (<0.01%) {original[2]}")
print(f"random sampling {args.samples} out of {len(original_stakes)}, {args.rounds} rounds")
prob = np.array(original_stakes)/sum_stakes
mins = {}
maxs = {}
for _ in range(args.rounds):
    choices = np.random.choice(original_stakes, size=args.samples, replace=False, p=prob)
    for (j, value) in enumerate(analyze_stakes(choices, sum_stakes)):
        mins[j] = min(mins.get(j, value), value)
        maxs[j] = max(maxs.get(j, value), value)
print(f"total {mins[0]*100/sum_stakes:2.2f}% to {maxs[0]*100/sum_stakes:2.2f}% high_stakes(>1%) "
      f"{mins[1]} to {maxs[1]} low_stakes(<0.01%%) {mins[2]} to {maxs[2]}")

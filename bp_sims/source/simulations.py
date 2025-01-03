import argparse
import sys
from enum import Enum
from typing import TypeAlias
import numpy as np
from numpy.random import exponential, poisson
from numpy.typing import NDArray
from scipy.stats import norm  # type: ignore
import json

Locations: TypeAlias = NDArray[np.float64]

class Event(Enum):
    BIRTH = 0
    DEATH = 1
    MUTATION = 2
    SAMPLE = 3

def event_rates(k: int, s: float, theta: float, r: float) -> dict[Event, float]:
    """Calculate the rate of each event type."""
    return {
        Event.BIRTH: k * (1 - s),
        Event.DEATH: k,
        Event.MUTATION: theta,
        Event.SAMPLE: r,
    }


def time_to_next(k: int, s: float, theta: float, r: float) -> float:
    """Generate the waiting time to the next event."""
    if k == 0:
        # If nothing is alive, jump to the next mutation; don't sample
        total_rate = theta
    else:
        total_rate = sum(event_rates(k, s, theta, r).values())
    return exponential(scale=1 / total_rate)


def choose_event(k: int, s: float, theta: float, r: float) -> Event:
    """Choose the type of the next event."""
    # If nothing is alive, jump to the next mutation; don't sample
    if k == 0:
        return Event.MUTATION
    rates = event_rates(k, s, theta, r)
    tot = sum(rates.values())
    choice = np.random.choice(len(Event), p=[rates[e] / tot for e in Event])
    return Event(choice)


def generate_zeros(t_zero: float, r: float) -> int:
    """Simulate the number of samples taken during times when zero carriers are alive"""
    return poisson(t_zero * r)


def get_alive(locations: Locations) -> NDArray[np.intp]:
    return np.where(~np.isnan(locations[:, 0]))[0]


def get_nan(locations: Locations) -> NDArray[np.intp]:
    return np.where(np.isnan(locations[:, 0]))[0]


def get_free_row(locations: Locations) -> int:
    """
    Get the index of the next free row in locations.

    Side effect: If there are no free rows, double the length of locations.
    """
    empty_row_indices = get_nan(locations)
    if len(empty_row_indices) > 0:
        return empty_row_indices[0]
    else:
        sys.stderr.write("No free rows. Doubling array size.\n")
        next_row = locations.shape[0]
        extend_locations(locations)
        return next_row


def extend_locations(locations: Locations) -> None:
    """Double the length of locations in-place."""
    old_length = locations.shape[0]
    locations.resize((2 * old_length, locations.shape[1]), refcheck=False)
    locations[old_length:] = np.nan


def wrap_locations(locations: Locations, L: float) -> Locations:
    return locations % L


def update_locations(
    locations: Locations, sigma: float, t_next: float, L: float
) -> Locations:
    alive_rows = get_alive(locations)
    if len(alive_rows) > 0:
        locations[alive_rows] += np.random.normal(
            loc=0, scale=sigma * np.sqrt(t_next), size=(len(alive_rows), 2)
        )
    locations = wrap_locations(locations, L)
    return locations

def get_centers_grid(L,n_side):
    coords = [i * L / n_side for i in range(n_side)]
    centers = [(x, y) for x in coords for y in coords]
    return centers

def wrapped_norm_pdf(x, loc, period: float, scale: float):
    # Include enough terms in the sum for good accuracy
    k_max = int(np.ceil(5 * scale / period))
    dens = 0
    for k in np.arange(-k_max, k_max + 1):
        dens += norm.pdf(
            x, loc=loc + k * period, scale=scale
        )
    return dens


def sampling_probability_wrapped(
    locations: Locations, centers:list[tuple[float,float]], w: float, L: float, rho: float
) -> list[float]:
    sampling_probs = []
    loc_alive = locations[get_alive(locations)]
    for c in centers:
        x1_dens = wrapped_norm_pdf(x=loc_alive[:,0],loc=c[0],scale=w,period=L)
        x2_dens = wrapped_norm_pdf(x=loc_alive[:,1],loc=c[1],scale=w,period=L)
        prod_dens = x1_dens * x2_dens
        sampling_probs.append(np.sum(prod_dens)/rho)
    return sampling_probs

def run_sim_spatial(
    s: float,
    mu: float,
    rho: float,
    r: float,
    sigma: float,
    time_limit: float,
    L: float,
    w: float,
    n_side: int,
    sampling_scheme: str,
) -> dict:
    """
    * Carriers appear de novo with rate `mu`*`rho`
    * Carriers give birth (split) with rate `1-s`
    * Carriers die at rate `1`
    * Take samples at rate `r`
    * Habitat is a square (0,L)x(0,L) with periodic boundary conditions

    Implement via Gillespie algorithm. At each step:
    1. Draw waiting time to next event
    2. Update locations of living carriers
    3. Select event type and apply it

    Data structures:
    * During simulation, store locations of individuals at the current time
    * At each sample point update the SFS distribution (array w/ pre-specified length)
    * Output SFS distribution
    """

    burnin = 10/s

    # parameter for total mutation rate
    N = rho * (L**2)
    theta = mu * N

    # keep track of individual level data
    # [x coord, y coord]
    n_start = 1000
    locations = np.full((n_start, 2), np.nan)

    # keep a running total of the time with zero carriers alive
    t_zero = 0.0

    # calculate centers
    if sampling_scheme == "wrapped_norm":
        centers = get_centers_grid(L,n_side)
    elif sampling_scheme == "uniform":
        centers = np.nan
        n_side = 1

    # track values of p
    sampled_p_list = []
    # initialize current time at 0
    time_running = 0.0
    while True:
        alive_rows = get_alive(locations)
        k = len(alive_rows)  # number of alive particles
        # draw time to next event & update time_running
        t_next = time_to_next(k, s, theta, r)
        time_running += t_next
        # if next time step exceeds limit, break
        if time_running > time_limit+burnin:
            break
        # if no lineages, add t_next to t_zero
        if time_running > burnin:
            if k == 0:
                t_zero += t_next
        # draw event type
        event = choose_event(k, s, theta, r)

        ### update spatial coordinates
        locations = update_locations(locations=locations, sigma=sigma, t_next=t_next, L=L)

        if event is Event.MUTATION:
            # add a new lineage at a random location
            next_row = get_free_row(locations)
            locations[next_row] = np.random.uniform(low=0.0, high=L, size=2)

        elif event is Event.DEATH:
            ## choose a random individual to die
            random_index = np.random.choice(alive_rows)
            locations[random_index] = np.nan

        elif event is Event.BIRTH:
            # choose parent at random from alive individuals
            parent_index = np.random.choice(alive_rows)
            # add new lineage with location of parent
            next_row = get_free_row(locations)
            locations[next_row] = locations[parent_index]

        elif event is Event.SAMPLE:
            if time_running > burnin:
                if sampling_scheme == 'wrapped_norm':
                    p = sampling_probability_wrapped(locations=locations, centers=centers, w=w, L=L, rho=rho)
                elif sampling_scheme == 'uniform':
                    p = [k / N]
                sampled_p_list.append(p)

    # Simulate the zero count SFS bin
    zero_samples = generate_zeros(t_zero, r)*n_side**2
    sampled_p_flattened = [item for sublist in sampled_p_list for item in sublist]

    results = {
        "s": s,
        "mu": mu,
        "rho": rho,
        "r": r,
        "sigma": sigma,
        "time_limit": time_limit,
        "L": L,
        "w": w,
        "n_side": n_side,
        "sampling_scheme": sampling_scheme,
        "sampled_p_flattened": sampled_p_flattened,
        "zero_samples": zero_samples,
        "centers": centers,
        "burnin": burnin,
        "N": N,
        "theta": theta
    }

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", type=float, help="selection coefficient")
    parser.add_argument("--mu", type=float, help="mutation rate")
    parser.add_argument("--dens", type=float, help="population density")
    parser.add_argument("-r", type=float, help="sampling rate")
    parser.add_argument(
        "--sigma", type=float, help="diffusion coefficient"
    )
    parser.add_argument(
        "--time_limit", type=float, help="time limit"
    )
    parser.add_argument("-L", type=float, help="habitat width")
    parser.add_argument("--seed", type=int, help="random string")
    parser.add_argument("-w", type=float, help="width for sampling kernel")
    parser.add_argument("--n_side", type=int, help="number of centers per side")
    parser.add_argument("--sampling_scheme",type=str,help="uniform or wrapped_norm")
    parser.add_argument("--json_out", type=str, help="json output filename")
    args = parser.parse_args()

    # set seed
    np.random.seed(args.seed)

    # run simulation
    results = run_sim_spatial(
        s=args.s,
        mu=args.mu,
        rho=args.dens,
        r=args.r,
        sigma=args.sigma,
        time_limit=args.time_limit,
        L=args.L,
        w=args.w,
        n_side=args.n_side,
        sampling_scheme=args.sampling_scheme
    )
    # add seed to results
    results['seed'] = args.seed

    # save output as json
    with open(args.json_out,"w") as file:
        json.dump(results,file)


if __name__ == "__main__":
    main()

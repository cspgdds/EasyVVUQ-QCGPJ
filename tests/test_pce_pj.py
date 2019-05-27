import os
import time
import numpy as np
import chaospy as cp
import easyvvuq as uq

from qcg.appscheduler.api.manager import Manager
from qcg.appscheduler.api.job import Jobs
from qcg.appscheduler.api.manager import LocalManager
from easypj.pj_configurator import PJConfigurator

# author: Jalal Lakhlili / Bartosz Bosak
__license__ = "LGPL"

cwd = os.getcwd()


def test_pce_pj(tmpdir):

    print("Running in directory: " + cwd)

    # establish available resources
    cores = 4

    # set location of log file
    # client_conf = {'log_file': tmpdir.join('api.log'), 'log_level': 'DEBUG'}

    # switch on debugging (by default in api.log file)
    client_conf = {'log_level': 'DEBUG'}

    # switch on debugging (by default in api.log file)
    m = LocalManager(['--nodes', str(cores)], client_conf)

    # This is for execution of the test using a separate (non-local) instance of PJManager
    #
    # get available resources
    # res = m.resources()
    # remove all jobs if they are already in PJM
    # (required when executed using the same QCG-Pilot Job Manager)
    # m.remove(m.list().keys())

    print("available resources:\n%s\n" % str(m.resources()))

    # Params for testing
    input_json = "tests/pce_pj/pce/pce_in.json"
    output_json = os.path.join(tmpdir, "out_pce.json")

    assert(os.path.exists(input_json))

    # Initialize Campaign object
    my_campaign = uq.Campaign(state_filename=input_json, workdir=tmpdir)

    # Define the parameters dictionary
    my_campaign.vary_param("kappa", dist=cp.Uniform(0.025, 0.075))
    my_campaign.vary_param("t_env", dist=cp.Uniform(15, 25))

    # Create the sampler
    my_sampler = uq.elements.sampling.PCESampler(
        my_campaign, polynomial_order=1)

    # Use the sampler
    my_campaign.add_runs(my_sampler)

    # Create PJ configurator
    pjc = PJConfigurator(my_campaign)
    pjc.init_runs_dir()

    # Save PJ configuration
    pjc.save()

    # Execute encode -> execute for each run using QCG-PJ
    for key, data in my_campaign.runs.items():
        encode_job = {
            "name": 'encode_' + key,
            "execution": {
                "exec": cwd + '/tests/pce_pj/pj_scripts/easyvvuq_encode',
                "args": [my_campaign.campaign_dir,
                         key],
                "wd": cwd,
                "stdout": my_campaign.campaign_dir + '/encode_' + key + '.stdout',
                "stderr": my_campaign.campaign_dir + '/encode_' + key + '.stderr'
            },
            "resources": {
                "numCores": {
                    "exact": 1
                }
            }
        }

        execute_job = {
            "name": 'execute_' + key,
            "execution": {
                "exec": cwd + '/tests/pce_pj/pj_scripts/easyvvuq_execute',
                "args": [my_campaign.campaign_dir,
                         key,
                         cwd + "/tests/pce_pj/pj_scripts/easyvvuq_app",
                         cwd + "/tests/pce_pj/pce/pce_model.py", "pce_in.json"],
                "wd": cwd,
                "stdout": my_campaign.campaign_dir + '/execute_' + key + '.stdout',
                "stderr": my_campaign.campaign_dir + '/execute_' + key + '.stderr'
            },
            "resources": {
                "numCores": {
                    "exact": 1
                }
            },
            "dependencies": {
                "after": ["encode_" + key]
            }
        }

        m.submit(Jobs().addStd(encode_job))
        m.submit(Jobs().addStd(execute_job))

    # wait for completion of all PJ tasks and terminate the PJ manager
    m.wait4all()
    m.finish()
    m.stopManager()
    m.cleanup()

    print("encode stdout:")
    print(open(my_campaign.campaign_dir + "/encode_Run_0.stdout", 'r').read())
    print("encode stderr:")
    print(open(my_campaign.campaign_dir + "/encode_Run_0.stderr", 'r').read())
    print("execute stdout:")
    print(open(my_campaign.campaign_dir + "/execute_Run_0.stdout", 'r').read())
    print("execute stderr:")
    print(open(my_campaign.campaign_dir + "/execute_Run_0.stderr", 'r').read())

    print("Aggregating the results")
    # Aggregate the results from all runs.
    output_filename = my_campaign.params_info["out_file"]["default"]
    output_columns = ["te", "ti"]

    aggregate = uq.elements.collate.AggregateSamples(
        my_campaign,
        output_filename=output_filename,
        output_columns=output_columns,
        header=0,
    )

    aggregate.apply()

    print("aggregated data:")
    print(open(my_campaign.data['files'][0], 'r').read())

    # Post-processing analysis
    print("Making the analysis")
    analysis = uq.elements.analysis.PCEAnalysis(
        my_campaign, value_cols=output_columns)

    stats, corr, sobols = analysis.apply()

    print("Done")
    return stats["te"], sobols["te"]


if __name__ == "__main__":
    start_time = time.time()

    stats, sobols = test_pce_pj("/tmp/")

    end_time = time.time()
    print('>>>>> elapsed time = ', end_time - start_time)

    # Plot statistical results
    __plot = True

    if __plot:
        import matplotlib.pyplot as plt
        mean = stats["mean"].to_numpy()
        std = stats["std"].to_numpy()
        var = stats["var"].to_numpy()

        s_kappa = sobols["kappa"].to_numpy()
        s_t_env = sobols["t_env"].to_numpy()

        t = np.linspace(0, 200, 150)

        fig1 = plt.figure()

        ax11 = fig1.add_subplot(111)
        ax11.plot(t, mean, 'g-', alpha=0.75, label='Mean')
        ax11.plot(t, mean - std, 'b-', alpha=0.25)
        ax11.plot(t, mean + std, 'b-', alpha=0.25)
        ax11.fill_between(
            t,
            mean - std,
            mean + std,
            alpha=0.25,
            label=r'Mean $\pm$ deviation')
        ax11.set_xlabel('Time')
        ax11.set_ylabel('Temperature', color='b')
        ax11.tick_params('y', colors='b')
        ax11.legend()

        ax12 = ax11.twinx()
        ax12.plot(t, var, 'r-', alpha=0.5)
        ax12.set_ylabel('Variance', color='r')
        ax12.tick_params('y', colors='r')

        ax11.grid()
        ax11.set_title('Statistical moments')

        fig2 = plt.figure()
        ax2 = fig2.add_subplot(111)
        ax2.plot(t, s_kappa, 'b-', label=r'$\kappa$')
        ax2.plot(t, s_t_env, 'g-', label=r'$t_{env}$')

        ax2.set_xlabel('Time')
        ax2.set_ylabel('Sobol indices')
        ax2.set_title('First order Sobol indices')
        ax2.grid()
        ax2.legend()

        plt.show()

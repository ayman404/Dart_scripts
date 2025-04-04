import pytools4dart as ptd

simu = ptd.simulation(name="simulation_test", empty=False, ncpu=4)
print(simu)

# run sequence
simu.run.sequence('sequence')
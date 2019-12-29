import sys, os
import numpy as np
from UGParameterEstimator import *
from testEvaluator import *
from skopt.plots import plot_evaluations


pm = ParameterManager()
pm.addParameter(DirectParameter("x1", 1.0, 0, 10))
pm.addParameter(DirectParameter("x2", 5.0, 0, 10))

result = Result("results_newton.pkl")
evaluator = TestEvaluator(pm, result)

optimizer = GaussNewtonOptimizer(LinearParallelLineSearch(evaluator), differencing=Optimizer.Differencing.pure_forward)

with evaluator:
    target = evaluator.evaluate([np.array([2.0,3.0])], transform=False, tag="target")[0]

result = optimizer.run(evaluator, pm.getInitialArray(), target, result=result)

print(evaluator)
evaluator.reset()

result = Result("results_scipy.pkl")


optimizer = GaussNewtonOptimizer(LinearParallelLineSearch(evaluator), differencing=Optimizer.Differencing.forward)
optimizer.run(evaluator, pm.getInitialArray(), target, result=result)


print(evaluator)
# evaluator.reset()
# result = Result("results_scipy.pkl")

# optimizer = BayesOptimizer(pm)
# optimizer.run(evaluator, pm.getInitialArray(), target, result=result)


# print(evaluator)


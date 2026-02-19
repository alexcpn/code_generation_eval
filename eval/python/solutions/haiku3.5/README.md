Haiku 3.5 wrote tests instead of an implementation. It imported from a nonexistent dependency_resolver module and wrote test functions. It completely misunderstood the prompt 
  — it was asked to write resolve(), Task, CyclicDependencyError, etc., but instead wrote tests for  them.
  
  This is a legitimate failure — the model didn't produce the requested code. That's a 0/15 and correctly shows Haiku 3.5's limitation: it confused "write this function" with "write tests    for this function."
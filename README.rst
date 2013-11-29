========
 freezr
========

What is **freezr**? Here's in a nutshell what freezr allows you to do:

* Define *domains*, which is just a method of grouping *accounts*.
* Define *accounts*, which map to an `AWS <http://aws.amazon.com/>`_
  accounts with access credentials.
* Define *projects*, tied to an *account*, and which defines *regions*
  and *filters* to split *instances* running on that account into
  three classes of instances, *saved*, *terminated* and *skipped*.
* Allows you to *freeze* a project, which will *stop* any *saved*
  instances, *terminate* any instance marked for *termination* (and
  not do anything about the rest).
* Allows you to *thaw* a (frozen) project, causing it to *start* all
  *saved* instances that are *stopped*.

In a sense, freezr is a web service with the goal of saving
money. Errr, that is, spending less money on AWS EC2 instances by
stopping and terminating instances that don't have to be up and
running. Freezr really helps to save money on a set of **narrowly
defined use cases**:

* You have to keep persistent (EBS-backed) instances available for a
  long time, but they don't have to be running all the time.

* You need self-help start / stop functionality on those, but either
  don't want to give everybody needed IAM credentials, or you need
  easier mechanism to do this than command-line tools or AWS console.

The motivation behind writing freezr is my work -- a cloud and
software consultancy -- where a typical customer project run the
devtest operation in the cloud: Jenkins, build slaves, test targets
and test runners etc. etc. Some of those resources are dynamic and are
automatically managed (slaves), but some are a lot
longer-running. During active development the costs incurred are just
part of development costs, typically a minuscule portion of developer
pay, for example. However the situation changes when moving from
active development into maintenance phase. You can't really run down
all the CI assets, as any changes (bug fixing, minor development) done
during maintenance *still needs to be tested*. So you cannot really
erase all of the infrastructure, like CI hosts for example.

So they end up costing you money. If the project has a low-intensity
maintenance phase, you are essentially severely eating into your
margins with those costs.

There a few things you can do to minimize your costs, but it's a bit
of a tradeoff:

* You could tune all persistent instances down to `t1.micro`
  instances. OTOH, depending on your use case your master might need a
  lot of CPU oomph or a lot of memory. It might not run reliably on
  smaller instances *at all*.

* You could get the project manager (if you have those) to start and
  stop instances whenever needed from the AWS console. OTOH, your
  project manager might not be really inclined to do that, not always
  remember to do that, and this would, from developer's perspective
  add an extra layer of management cruft.

* You could let developers do the above stuff. They'd write scripts to
  automate that and stuff them into the project repo, making it a
  little easier, but still, *someone* would have to remember to do
  that and *all* of them would need to know how to do that on every
  particular project.

So freezr aims to be a **simple** to use service for starting and
stopping project assets in a **controlled** manner.

That's a bit of a long-winded explanation. (Reminder to self: rewrite
this text.)

What it does and doesn't do
===========================

Currently freezr does:

* Has REST API to CRUD resources and to freeze/thaw projects

What it does not do (all of these are planned):

* Not easy to setup
* No user authentication or access control
* No web UI
* Not production quality in any manner

How to use it?
==============

Currently: you are on your own. This is very much still work in
progress.

How to contribute
=================

Fork, submit patches. See planned list above or even better, check the
`taskboard at trello <http://bit.ly/1eF8d3c>`_. Contact me and ask to
be added to the board and project.

/**
 * @file dm_mixture_model.cpp
 * @author Chase Geigle
 *
 * Fits a variant of a Dirichlet-Multinomial Mixture Model to a collection
 * of sequences.
 **/

#include <fstream>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <random>
#include <sstream>

#include "meta/io/filesystem.h"
#include "meta/logging/logger.h"
#include "meta/math/fastapprox.h"
#include "meta/meta.h"
#include "meta/stats/multinomial.h"
#include "meta/util/iterator.h"
#include "meta/util/progress.h"
#include "meta/util/random.h"
#include "meta/util/sparse_vector.h"

using namespace meta;

namespace py = pybind11;

MAKE_NUMERIC_IDENTIFIER(session_id, uint64_t)
MAKE_NUMERIC_IDENTIFIER(action_type, uint64_t)
MAKE_NUMERIC_IDENTIFIER(user_id, uint64_t)

namespace pybind11
{
namespace detail
{

template <class Type>
struct identifier_caster
{
    using underlying_type = typename Type::underlying_type;
    using type_conv = make_caster<underlying_type>;

    PYBIND11_TYPE_CASTER(Type, _("id[") + type_conv::name() + _("]"));

    bool load(handle src, bool convert)
    {
        type_conv conv;
        if (!conv.load(src, convert))
            return false;
        value = Type{(underlying_type)conv};
        return true;
    }

    static handle cast(const Type& src, return_value_policy policy,
                       handle parent)
    {
        return type_conv::cast(static_cast<underlying_type>(src), policy,
                               parent);
    }
};

template <class Tag, class T>
struct type_caster<meta::util::numerical_identifier<Tag, T>>
    : identifier_caster<meta::util::numerical_identifier<Tag, T>>
{
};

template <class Tag, class T>
struct type_caster<meta::util::identifier<Tag, T>>
    : identifier_caster<meta::util::identifier<Tag, T>>
{
};
} // namespace detail
} // namespace pybind11

class dm_mixture_model
{
  public:
    // session[i] == # of times action i was taken in that session
    using session_type = util::sparse_vector<action_type, uint64_t>;
    // sequences[i] == one session for a specific user
    using sequences_type = std::vector<session_type>;
    // training_data[i] == one user in the collection
    using training_data_type = std::vector<sequences_type>;

    struct options_type
    {
        uint8_t num_topics = 5;
        uint64_t num_actions;
        double alpha = 0.1;
        double beta = 0.1;
    };

    template <class RandomNumberEngine>
    dm_mixture_model(const training_data_type& training, options_type opts,
                     RandomNumberEngine&& rng)
        : topic_assignments_(
              std::accumulate(std::begin(training), std::end(training), 0ul,
                              [](uint64_t accum, const sequences_type& seqs) {
                                  return accum + seqs.size();
                              })),
          // initialize all topics with the same prior pseudo-counts
          topics_(opts.num_topics,
                  stats::multinomial<action_type>{stats::dirichlet<action_type>(
                      opts.beta, opts.num_actions)}),
          topic_proportions_(
              training.size(),
              stats::multinomial<topic_id>{
                  stats::dirichlet<topic_id>(opts.alpha, opts.num_topics)})
    {
        initialize(training, std::forward<RandomNumberEngine>(rng));
    }

    template <class RandomNumberEngine, class ProgressReporter>
    void run(const training_data_type& training, uint64_t num_iters,
             RandomNumberEngine&& rng, ProgressReporter&& progress)
    {
        progress(0, num_iters, topic_assignments_.size(),
                 topic_assignments_.size(), log_joint_likelihood());
        for (uint64_t iter = 1; iter <= num_iters; ++iter)
        {
            perform_iteration(training, std::forward<RandomNumberEngine>(rng),
                              [&](uint64_t idx, uint64_t total) {
                                  progress(iter, num_iters, idx, total);
                              });
            progress(iter, num_iters, topic_assignments_.size(),
                     topic_assignments_.size(), log_joint_likelihood());
        }
    }

    template <class RandomNumberEngine, class ProgressReporter>
    void perform_iteration(const training_data_type& training,
                           RandomNumberEngine&& rng,
                           ProgressReporter&& progress)
    {
        const auto total = topic_assignments_.size();
        uint64_t x = 0;
        for (user_id i{0}; i < training.size(); ++i)
        {
            for (doc_id j{0}; j < training[i].size(); ++j)
            {
                // remove counts
                auto old_z = topic_assignments_[x];
                topic_proportions_[i].decrement(old_z, 1.0);
                for (const auto& pr : training[i][j])
                {
                    topics_[old_z].decrement(pr.first, pr.second);
                }

                // sample new topic
                auto z = sample_topic(i, training[i][j],
                                      std::forward<RandomNumberEngine>(rng));
                topic_assignments_[x] = z;

                // update counts
                topic_proportions_[i].increment(z, 1.0);
                for (const auto& pr : training[i][j])
                {
                    topics_[z].increment(pr.first, pr.second);
                }
                progress(++x, total);
            }
        }
    }

    double log_joint_likelihood() const
    {
        // log p(w, z) = log p(w | z)p(z) = log p(w|z) + log p(z)
        //
        // both p(w|z) and p(z) are Dirichlet-multinomial distributions
        auto log_likelihood = 0.0;

        // log p(w|z)
        for (const auto& topic : topics_)
        {
            log_likelihood += dm_log_likelihood(topic);
        }

        // log p(z)
        for (const auto& theta : topic_proportions_)
        {
            log_likelihood += dm_log_likelihood(theta);
        }

        return log_likelihood;
    }

    void save(const std::string& prefix) const
    {
        if (!filesystem::exists(prefix))
            filesystem::make_directories(prefix);

        std::ofstream topics_file{prefix + "/topics.bin", std::ios::binary};
        io::packed::write(topics_file, topics_);

        std::ofstream topic_proportions_file{prefix + "/topic-proportions.bin",
                                             std::ios::binary};
        io::packed::write(topic_proportions_file, topic_proportions_);
    }

    topic_id topic_assignment(session_id id) const
    {
        return topic_assignments_[id];
    }

    double action_probability(topic_id id, action_type aid) const
    {
        return topics_[id].probability(aid);
    }

    double role_probability(user_id uid, topic_id tid) const
    {
        return topic_proportions_[uid].probability(tid);
    }

  private:
    template <class RandomNumberEngine>
    void initialize(const training_data_type& training,
                    RandomNumberEngine&& rng)
    {
        printing::progress progress{" > Initialization: ",
                                    topic_assignments_.size()};

        // proceed like a normal sampling pass, but without removing any counts
        uint64_t x = 0;
        for (user_id i{0}; i < training.size(); ++i)
        {
            for (doc_id j{0}; j < training[i].size(); ++j)
            {
                auto z = sample_topic(i, training[i][j],
                                      std::forward<RandomNumberEngine>(rng));
                topic_assignments_[x] = z;
                topic_proportions_[i].increment(z, 1.0);
                for (const auto& pr : training[i][j])
                {
                    topics_[z].increment(pr.first, pr.second);
                }
                progress(++x);
            }
        }
    }

    template <class RandomNumberEngine>
    topic_id sample_topic(user_id i, const session_type& session,
                          RandomNumberEngine&& rng)
    {
        //
        // compute sample using the Gumbel-max trick:
        // https://stats.stackexchange.com/questions/64081
        //
        // This is done to avoid underflow issues due to the |d|
        // multiplications of probabilities in the second term of the
        // sampling proportion equation for the Gibbs sampler.
        //
        topic_id result{0};
        auto max_value = std::numeric_limits<float>::lowest();
        std::uniform_real_distribution<float> dist{0, 1};

        const auto num_topics = topics_.size();
        for (topic_id z{0}; z < num_topics; ++z)
        {
            // compute the sampling probability (up to proportionality) in
            // log-space to avoid underflow
            auto denom = static_cast<float>(topics_[z].counts());
            auto log_prob = fastapprox::fastlog(
                static_cast<float>(topic_proportions_[i].probability(z)));
            uint64_t j = 0;
            for (const auto& pr : session)
            {
                const auto& word = pr.first;
                const auto& count = pr.second;

                for (uint64_t i = 0; i < count; ++i)
                {
                    log_prob += fastapprox::fastlog(
                        static_cast<float>(topics_[z].counts(word)) + i);
                    log_prob -= fastapprox::fastlog(denom + j);
                    ++j;
                }
            }

            // apply the Gumbel-max trick to update the sample
            auto rnd = dist(rng);
            auto gumbel_noise = -fastapprox::fastlog(-fastapprox::fastlog(rnd));

            if (log_prob + gumbel_noise > max_value)
            {
                result = z;
                max_value = log_prob + gumbel_noise;
            }
        }

        return result;
    }

    template <class T>
    double dm_log_likelihood(const stats::multinomial<T>& dist) const
    {
        auto log_likelihood = std::lgamma(dist.prior().pseudo_counts());
        log_likelihood -= std::lgamma(dist.counts());

        dist.each_seen_event([&](const T& val) {
            log_likelihood += std::lgamma(dist.counts(val));
            log_likelihood -= std::lgamma(dist.prior().pseudo_counts(val));
        });

        return log_likelihood;
    }

    /// the topic assignment for each session
    std::vector<topic_id> topic_assignments_;

    /**
     * The action distributions for each role. Doubles as storage for the
     * count information for each role.
     */
    std::vector<stats::multinomial<action_type>> topics_;

    /**
     * The topic distributions for each network. Doubles as storage for the
     * count information for each network.
     */
    std::vector<stats::multinomial<topic_id>> topic_proportions_;
};

PYBIND11_MODULE(mdmm_sampler, m)
{
    m.doc() = "Collapsed Gibbs sampler for MDMM behavior models";

    py::class_<dm_mixture_model> mdmm{m, "MDMM"};

    using session_type = dm_mixture_model::session_type;
    py::class_<session_type>{m, "Session"}
        .def(py::init<>())
        .def(py::init<uint64_t>())
        .def(py::init<const session_type&>())
        .def(py::init([](py::iterable iter) {
            using pair_type = session_type::pair_type;
            auto cast_fn = [](py::handle h) { return h.cast<pair_type>(); };
            return session_type(
                util::make_transform_iterator(iter.begin(), cast_fn),
                util::make_transform_iterator(iter.end(), cast_fn));
        }))
        .def("__len__", &session_type::size)
        .def("__iter__",
             [](session_type& fv) {
                 return py::make_iterator(fv.begin(), fv.end());
             },
             py::keep_alive<0, 1>())
        .def("__getitem__",
             [](const session_type& fv, action_type id) { return fv.at(id); })
        .def("__setitem__",
             [](session_type& fv, action_type id, double val) { fv[id] = val; })
        .def("clear", &session_type::clear)
        .def("shrink_to_fit", &session_type::shrink_to_fit)
        .def("condense", &session_type::condense)
        .def("__str__", [](const session_type& fv) {
            std::stringstream ss;
            util::string_view padding = "";
            ss << '[';
            for (const auto& pr : fv)
            {
                ss << padding << '(' << pr.first << ", " << pr.second << ')';
                padding = ", ";
            }
            ss << ']';
            return ss.str();
        });

    using options_type = dm_mixture_model::options_type;
    py::class_<options_type>{mdmm, "Options"}
        .def(py::init([](uint8_t num_topics, uint64_t num_actions, double alpha,
                         double beta) {
                 options_type o{};
                 o.num_topics = num_topics;
                 o.num_actions = num_actions;
                 o.alpha = alpha;
                 o.beta = beta;
                 return o;
             }),
             py::arg("num_topics") = 5, py::arg("num_actions"),
             py::arg("alpha") = 0.1, py::arg("beta") = 0.1)
        .def_readwrite("num_topics", &options_type::num_topics)
        .def_readwrite("num_actions", &options_type::num_actions)
        .def_readwrite("alpha", &options_type::alpha)
        .def_readwrite("beta", &options_type::beta);

    auto rng_mod = m.def_submodule("random", "RNG facilities for the sampler");

    py::class_<random::xoroshiro128>{rng_mod, "Xoroshiro128"}
        .def(py::init<uint64_t>())
        .def(py::init<uint64_t, uint64_t>())
        .def("__call__", &random::xoroshiro128::operator());

    using training_data_type = dm_mixture_model::training_data_type;
    mdmm.def(py::init<const training_data_type&, options_type,
                      random::xoroshiro128&>())
        .def("run",
             &dm_mixture_model::run<random::xoroshiro128&, py::function&>)
        .def("action_probability", &dm_mixture_model::action_probability)
        .def("role_probability", &dm_mixture_model::role_probability)
        .def("topic_assignment", &dm_mixture_model::topic_assignment);
}
